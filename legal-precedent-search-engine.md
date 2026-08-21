# Legal Precedent Search Engine
### System Design & Build Specification — Tries, Inverted Indexes, Citation Graphs, Ranking

---

## 0. Scope & Intent

This is a from-scratch information-retrieval system for searching case law and statutes. It is deliberately **not** "wrap Elasticsearch" — the point of the project is to implement the three core IR data structures (trie, inverted index, citation graph) and a composite ranking function yourself, so you understand what production search engines (Lucene/Solr, Elasticsearch, Westlaw's proprietary index) are actually doing underneath.

**Core capabilities to deliver:**
1. Prefix / autocomplete search over case names, citations, statute numbers, judge names → **Trie**
2. Full-text relevance search over opinion text → **Inverted Index + BM25**
3. Authority / precedential-weight scoring via citation network → **Directed Graph + PageRank/HITS**
4. A single combined ranking function that merges (2) and (3), plus court-hierarchy and recency signals

---

## 1. Architecture

```
                          ┌────────────────────┐
                          │   Corpus Ingestion   │
                          │  (raw case files:    │
                          │  CourtListener/CAP,   │
                          │  JSON/XML/HTML)       │
                          └──────────┬───────────┘
                                     │
                     ┌───────────────┼────────────────┐
                     ▼               ▼                ▼
             ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐
             │  Text Pipeline │ │ Citation      │ │ Metadata Store    │
             │  (tokenize,    │ │ Extractor     │ │ (court, date,     │
             │  normalize,    │ │ (regex/NER on │ │  judge, docket)   │
             │  stopwords)    │ │  citation fmt)│ │                    │
             └───────┬────────┘ └──────┬───────┘ └─────────┬──────────┘
                     ▼                 ▼                   │
          ┌────────────────┐  ┌────────────────┐           │
          │ Inverted Index  │  │ Citation Graph  │           │
          │ Builder (SPIMI) │  │ Builder (adj.   │           │
          │                 │  │ list, directed) │           │
          └────────┬────────┘  └────────┬────────┘           │
                    │                    │                    │
                    ▼                    ▼                    │
          ┌────────────────┐  ┌────────────────┐              │
          │ Postings Store  │  │ PageRank /      │              │
          │ (term → docIDs, │  │ HITS Authority  │              │
          │  positions, tf) │  │ Scores          │              │
          └────────┬────────┘  └────────┬────────┘              │
                    │                    │                       │
                    └──────────┬─────────┴───────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   Query Engine       │
                    │ • Trie prefix lookup │
                    │ • BM25 scoring       │
                    │ • Authority blend    │
                    │ • Filters (court,    │
                    │   date, jurisdiction)│
                    └──────────┬───────────┘
                               ▼
                    ┌─────────────────────┐
                    │   REST/GraphQL API   │
                    └─────────────────────┘
```

---

## 2. Data Model

### 2.1 Case Document Schema

```json
{
  "doc_id": "us-supreme-court-1966-miranda-v-arizona",
  "case_name": "Miranda v. Arizona",
  "citation": "384 U.S. 436 (1966)",
  "court": "U.S. Supreme Court",
  "court_level": 1,
  "jurisdiction": "US-Federal",
  "date_decided": "1966-06-13",
  "judges": ["Warren, C.J.", "Black, J.", "..."],
  "opinion_text": "full plain-text opinion...",
  "headnotes": ["..."],
  "citations_out": ["escobedo-v-illinois-1964", "gideon-v-wainwright-1963"],
  "practice_areas": ["criminal-procedure", "constitutional-law"],
  "treatment_signals": {
    "followed_by": ["..."],
    "distinguished_by": ["..."],
    "overruled_by": []
  }
}
```

### 2.2 Citation Edge Schema (Graph)

```
Edge: (citing_case_id, cited_case_id, treatment_type, weight)
treatment_type ∈ {followed, distinguished, criticized, overruled, cited_generally}
weight: float, derived from treatment_type (see §5.3)
```

Court-level enum (used for authority weighting, US example — adapt to your jurisdiction):
```
1 = Supreme Court
2 = Circuit / Appellate Court
3 = District / Trial Court
4 = Administrative / Tribunal
```

---

## 3. Data Structure 1 — Trie (Prefix Search / Autocomplete)

### 3.1 Purpose
- Autocomplete for case names, statute citations (`"384 U.S. 4—"` → `384 U.S. 436`), judge surnames, legal terms of art (`"habeas cor—"` → `habeas corpus`).
- O(L) lookup where L = query length, independent of corpus size — critical for a responsive UI.

### 3.2 Node Structure

```python
class TrieNode:
    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.is_end_of_term: bool = False
        self.doc_ids: set[str] = set()      # docs where this exact term/name appears
        self.term_frequency: int = 0        # for autocomplete ranking (popularity)
```

### 3.3 Core Operations

```python
class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, term: str, doc_id: str):
        node = self.root
        for ch in term.lower():
            node = node.children.setdefault(ch, TrieNode())
        node.is_end_of_term = True
        node.doc_ids.add(doc_id)
        node.term_frequency += 1

    def _walk(self, prefix: str) -> TrieNode | None:
        node = self.root
        for ch in prefix.lower():
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def autocomplete(self, prefix: str, k: int = 10) -> list[str]:
        node = self._walk(prefix)
        if node is None:
            return []
        results = []
        self._collect(node, prefix, results)
        results.sort(key=lambda x: -x[1])          # rank by term_frequency
        return [term for term, _freq in results[:k]]

    def _collect(self, node: TrieNode, prefix: str, out: list):
        if node.is_end_of_term:
            out.append((prefix, node.term_frequency))
        for ch, child in node.children.items():
            self._collect(child, prefix + ch, out)
```

### 3.4 Production Considerations
- **Compressed trie (radix tree)**: collapse single-child chains to reduce memory — matters at 1M+ case names / citation strings.
- **Ternary Search Tree (TST)** is a reasonable alternative if memory is tighter than lookup-speed requirements.
- Build a **separate trie per entity type** (case names, citations, judges, terms-of-art) rather than one mega-trie — keeps autocomplete results precise and avoids irrelevant cross-type matches.
- Citation-format trie should be built on a **normalized citation string** (strip spaces/punctuation variance: `"384 U.S. 436"` vs `"384 US 436"` vs `"384US436"`) before insertion, with a canonical form stored at the terminal node.

**Complexity:** Insert O(L), Search O(L), Autocomplete O(L + Z) where Z = size of result subtree.

---

## 4. Data Structure 2 — Inverted Index (Full-Text Relevance Search)

### 4.1 Pipeline

```
raw opinion text
   → tokenize (word boundaries, handle "§", "¶", case citations as atomic tokens)
   → lowercase
   → remove stopwords (use a LEGAL-DOMAIN stopword list — "court," "plaintiff," "defendant"
     may or may not be stopwords depending on whether you want party-role search)
   → stem/lemmatize (Porter/Snowball stemmer, or a legal-aware lemmatizer —
     careful: stemming "liable" → "liabl" can hurt phrase queries, consider lemmatization instead)
   → emit (term, doc_id, position) tuples
```

### 4.2 Index Structure

```python
# Postings list per term
class PostingEntry:
    doc_id: str
    term_freq: int
    positions: list[int]     # needed for phrase queries ("beyond a reasonable doubt")

# term -> sorted list[PostingEntry], sorted by doc_id for merge-based boolean AND/OR
InvertedIndex = dict[str, list[PostingEntry]]

# Also maintain:
doc_lengths: dict[str, int]      # tokens per doc, needed for BM25 length normalization
avg_doc_length: float
doc_frequency: dict[str, int]    # df(term) = number of docs containing term, for IDF
N: int                            # total number of documents
```

### 4.3 Index Construction — SPIMI (Single-Pass In-Memory Indexing)

At corpus scale (hundreds of thousands of opinions, each 5–50 pages), do **not** try to build the full index in RAM in one pass.

```
for each document block that fits in memory:
    build a partial inverted index in memory
    sort terms alphabetically
    flush to disk as a sorted run

after all blocks processed:
    k-way merge all sorted runs into the final index (like external merge sort)
    write postings compressed (see 4.5)
```

This is the same strategy Lucene uses internally (segment merging).

### 4.4 Boolean & Phrase Query Support

- **AND**: merge-intersect two postings lists in O(len(list1) + len(list2)) — since lists are doc_id-sorted, this is a two-pointer merge, not a nested loop.
- **Phrase query**: after intersecting doc sets, check that `positions` lists contain consecutive integers across the query terms (positional intersection).

### 4.5 Compression (needed once corpus > ~100k documents)
- **Delta-encode doc_id gaps** in postings lists (doc IDs sorted ascending → store gaps, not absolute IDs).
- **Variable-byte encoding** for gaps and term frequencies.
- Consider a skip-list structure over long postings lists (common terms like "court") to accelerate AND-merges.

**Complexity:** Build O(T log T) per block (T = tokens), query intersection O(min(|P1|,|P2|)) with skip pointers.

---

## 5. Data Structure 3 — Citation Graph (Precedential Authority)

### 5.1 Why a Graph
Relevance to a text query is necessary but not sufficient for legal search — a case can be textually relevant and legally dead (overruled). Courts and researchers care about **authority**: how heavily-cited and how positively-treated a precedent is. This mirrors how Shepard's/KeyCite work, and structurally is the same problem PageRank solves for the web.

### 5.2 Graph Structure

```python
class CitationGraph:
    def __init__(self):
        self.adj: dict[str, list[tuple[str, float]]] = {}   # citing -> [(cited, weight)]
        self.reverse_adj: dict[str, list[tuple[str, float]]] = {}  # cited -> [(citing, weight)]

    def add_edge(self, citing_id: str, cited_id: str, treatment: str):
        w = TREATMENT_WEIGHT[treatment]
        self.adj.setdefault(citing_id, []).append((cited_id, w))
        self.reverse_adj.setdefault(cited_id, []).append((citing_id, w))
```

### 5.3 Treatment Weights

Not all citations are equal — a case that *distinguishes* or is *overruled by* a later case should not contribute the same authority signal as one that is *followed*.

```python
TREATMENT_WEIGHT = {
    "followed": 1.0,
    "cited_generally": 0.6,
    "distinguished": 0.3,
    "criticized": 0.2,
    "overruled": -1.0,      # negative signal — flag prominently, exclude from positive authority sum
}
```

### 5.4 Authority Ranking — PageRank over the Citation Graph

Precedent authority is a fixed-point problem: a case is authoritative if it is cited by other authoritative cases (with positive treatment).

```python
def pagerank(graph: CitationGraph, d: float = 0.85, iterations: int = 50, tol: float = 1e-6):
    nodes = list(graph.adj.keys() | graph.reverse_adj.keys())
    N = len(nodes)
    score = {n: 1.0 / N for n in nodes}

    for _ in range(iterations):
        new_score = {n: (1 - d) / N for n in nodes}
        for citing, edges in graph.adj.items():
            positive_edges = [(c, w) for c, w in edges if w > 0]
            out_weight_sum = sum(w for _, w in positive_edges) or 1.0
            for cited, w in positive_edges:
                new_score[cited] += d * score[citing] * (w / out_weight_sum)

        delta = sum(abs(new_score[n] - score[n]) for n in nodes)
        score = new_score
        if delta < tol:
            break
    return score
```

**Court-weighted variant:** multiply each case's PageRank contribution by its `court_level` inverse weight (a Supreme Court citation should carry more authority-transfer than a district court citation citing the same case) — this is a straightforward modification to the `d * score[citing] * ...` term: pre-multiply `score[citing]` by a court-tier coefficient before propagating.

### 5.5 Alternative: HITS (Hubs & Authorities)
If you want to distinguish "landmark cases" (authorities, heavily cited) from "comprehensive survey opinions" (hubs, cite many things), implement HITS as a secondary/optional signal — it's a natural extension once PageRank is working, and is a good "if time permits" addition.

### 5.6 Overruled/Bad-Law Detection
Run a separate traversal: any case with an incoming `overruled` edge is flagged `is_overruled = True` and should be either excluded from default results or shown with a prominent "Overruled by X" badge — this is a hard product requirement for a legal tool, not optional polish. Do a transitive check too: if case A overrules B, and C relies primarily on B's holding, C should at minimum surface a caution flag (this is a stretch goal — full Shepardizing-grade transitive treatment analysis is a research problem in itself).

**Complexity:** PageRank O(V + E) per iteration, converges in ~50 iterations for typical citation-graph structures.

---

## 6. Ranking — Combining Relevance and Authority

### 6.1 BM25 (Textual Relevance)

Industry-standard, outperforms raw TF-IDF, and is what Elasticsearch/Lucene use by default — implement this rather than plain TF-IDF.

```
BM25(D, Q) = Σ_{term ∈ Q}  IDF(term) · [ tf(term, D) · (k1 + 1) ] / [ tf(term, D) + k1 · (1 − b + b · |D| / avgdl) ]

IDF(term) = ln( (N − df(term) + 0.5) / (df(term) + 0.5) + 1 )

k1 ≈ 1.2–2.0   (term frequency saturation)
b  ≈ 0.75       (length normalization strength)
```

```python
import math

def bm25_score(query_terms, doc_id, index: InvertedIndex, doc_lengths, avg_doc_length, N, k1=1.5, b=0.75):
    score = 0.0
    for term in query_terms:
        postings = index.get(term, [])
        entry = next((p for p in postings if p.doc_id == doc_id), None)
        if not entry:
            continue
        df = len(postings)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        tf = entry.term_freq
        dl = doc_lengths[doc_id]
        denom = tf + k1 * (1 - b + b * dl / avg_doc_length)
        score += idf * (tf * (k1 + 1)) / denom
    return score
```

### 6.2 Composite Legal Relevance Score

```
FinalScore(D, Q) =  α · BM25_norm(D, Q)
                   + β · Authority_norm(D)          (PageRank score, min-max normalized)
                   + γ · CourtWeight(D)              (1.0 / 0.75 / 0.5 / 0.25 by court_level)
                   + δ · RecencyBoost(D)             (optional — legal research often prefers
                                                       CURRENT good law, not just old landmark cases)
                   − ε · OverruledPenalty(D)          (large penalty/exclusion if is_overruled)

  suggested starting weights: α=0.5, β=0.25, γ=0.15, δ=0.1, ε = hard filter, not a weight
```

Normalize each component to [0, 1] (min-max or z-score across the candidate result set) before combining — BM25 and PageRank live on completely different numeric scales and must not be summed raw.

**Design note:** treat `α..δ` as tunable, exposed via config, not hardcoded — you'll want to A/B test them once you have any usage data or a labeled relevance test set (§9).

### 6.3 Query-Time Flow

```
1. Parse query → extract free-text terms + structured filters (court, date range, jurisdiction)
2. If query looks like a citation or partial case name → Trie prefix lookup → direct jump / suggestions
3. Else → tokenize query same as indexing pipeline
4. Boolean-AND intersect postings lists across query terms → candidate doc set
   (fallback to OR / relaxed matching if AND yields too few results)
5. Apply structured filters (court, jurisdiction, date range) to candidate set
6. BM25-score candidates
7. Look up precomputed PageRank/authority score per candidate (precomputed offline, not at query time)
8. Compute FinalScore, exclude/flag overruled cases
9. Sort, paginate, return with highlighted snippets (positions from postings give you snippet windows for free)
```

---

## 7. Tech Stack Recommendation

| Layer | Recommendation | Why |
|---|---|---|
| Indexing/query core | Python (prototype) → Go or Rust (production) | Python for fast iteration on the DS&A logic; Go/Rust if you need real query latency at scale |
| Persistent postings store | Custom binary files with an offset table, OR SQLite/RocksDB as a key-value backing store | Avoid a full RDBMS for postings — key-value access pattern fits better |
| Metadata/relational data | PostgreSQL | Court, judge, date, jurisdiction filters are naturally relational |
| Graph storage | Adjacency list in-memory (Python dict) for < ~1M nodes; Neo4j or a custom edge-list-on-disk if it outgrows RAM | PageRank needs fast in-memory traversal |
| API | FastAPI (Python) or a Go HTTP server | Matches your existing stack familiarity |
| Frontend (optional) | Next.js, with the Trie-backed autocomplete hitting a `/suggest` endpoint | Consistent with typical modern search UX |

Given your existing stack (Next.js, viem/wagmi, Solidity/Foundry background), a natural pairing is: **FastAPI or Node/TS backend for the IR core + Next.js frontend**, keeping this project's Web3 surface area at zero unless you deliberately want to explore something like an on-chain-anchored citation-integrity layer as a stretch goal (§10).

---

## 8. Implementation Roadmap

**Phase 1 — Corpus & Ingestion (Week 1)**
- Source a real dataset: [CourtListener bulk data](https://www.courtlistener.com/help/api/bulk-data/) or the [Caselaw Access Project (CAP)](https://case.law/) — both provide structured case text + metadata, free.
- Parse into the Document Schema (§2.1). Extract citations via regex against standard citation formats (Bluebook), store as `citations_out`.

**Phase 2 — Trie (Week 1–2)**
- Implement trie, build tries for case names + citations.
- Build `/suggest?prefix=` endpoint, benchmark p99 latency.

**Phase 3 — Inverted Index (Week 2–3)**
- Tokenizer + legal stopword list + stemmer.
- SPIMI-style index build, boolean AND/OR, phrase queries.
- BM25 scoring, benchmark on a query set.

**Phase 4 — Citation Graph + PageRank (Week 3–4)**
- Build adjacency list from `citations_out`.
- Implement PageRank, validate convergence, sanity-check known landmark cases (e.g., *Marbury v. Madison*) score highly.
- Implement overruled-detection flagging.

**Phase 5 — Composite Ranking + API (Week 4–5)**
- Merge BM25 + PageRank + court weight + recency into FinalScore.
- Build the query API end-to-end with filters and pagination.
- Add snippet highlighting from stored term positions.

**Phase 6 — Evaluation & Tuning (Week 5–6)**
- Build a small labeled relevance test set (§9), tune α/β/γ/δ.
- Load-test with corpus at target scale; add compression (§4.5) if needed.

---

## 9. Evaluation

Standard IR project — don't skip this, it's what separates a working demo from something you can defend as "good."

- **Precision@k / Recall@k** on a hand-labeled query set (pick 20–30 realistic legal queries, manually judge top-10 relevance).
- **NDCG (Normalized Discounted Cumulative Gain)** — rewards putting the most relevant *and* most authoritative results first, which is exactly what this system optimizes for.
- **Mean Reciprocal Rank (MRR)** for citation/case-name lookup via the trie (did the correct case appear as the #1 autocomplete suggestion?).
- Sanity-test the overruled-flagging logic against known overruled cases (e.g., *Plessy v. Ferguson* overruled by *Brown v. Board of Education*) as a regression test.

---

## 10. Stretch Goals (optional, in increasing difficulty)

1. **Semantic search layer**: embed opinion text with a sentence-transformer model, add a vector-similarity re-ranking pass alongside BM25 (hybrid search) — catches conceptually-similar cases that don't share exact vocabulary.
2. **Learning-to-rank**: once you have query logs / labeled data, replace the hand-tuned α/β/γ/δ linear blend with a learned model (e.g., LambdaMART) over the same features.
3. **Shepardizing-grade transitive treatment analysis**: propagate "bad law" signals through the citation graph rather than only flagging direct overrule edges.
4. **On-chain citation-integrity anchoring**: given your Web3 background, an interesting (non-essential) extension is hashing each case's citation graph snapshot and anchoring the root on-chain periodically, so citation-graph tampering/rewriting is publicly auditable — this is a genuinely novel angle for a legal-tech portfolio piece, but treat it as a v2 idea, not part of the core deliverable.

---

## 11. Suggested Folder Structure

```
legal-precedent-search/
├── ingestion/
│   ├── fetch_corpus.py
│   ├── citation_extractor.py
│   └── schema.py
├── index/
│   ├── trie.py
│   ├── inverted_index.py
│   ├── spimi_builder.py
│   └── compression.py
├── graph/
│   ├── citation_graph.py
│   ├── pagerank.py
│   └── overrule_detection.py
├── ranking/
│   ├── bm25.py
│   └── composite_score.py
├── api/
│   ├── main.py                # FastAPI app
│   ├── routes/
│   │   ├── search.py
│   │   └── suggest.py
├── eval/
│   ├── labeled_queries.json
│   └── metrics.py
├── tests/
└── README.md
```

---

## 12. Complexity Summary

| Structure | Build | Query |
|---|---|---|
| Trie | O(total characters inserted) | O(L) prefix lookup, O(L+Z) autocomplete |
| Inverted Index | O(T log T) per block (SPIMI) | O(min list length) boolean AND with skip pointers |
| Citation Graph + PageRank | O(V+E) per PageRank iteration, ~50 iterations | O(1) authority lookup (precomputed) |
| Composite Ranking | — | O(k log k) sort over candidate set of size k |
