import time
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# Internal imports
from ingestion.schema import CaseDocument, SearchResponse, SearchResult
from ingestion.corpus_loader import get_mock_corpus
from index.tokenizer import tokenize, stem_word
from index.trie import AutocompleteManager
from index.inverted_index import InvertedIndex
from graph.citation_graph import CitationGraph
from graph.pagerank import compute_pagerank
from graph.overrule_detection import detect_overruled_cases
from ranking.bm25 import compute_bm25
from ranking.composite_score import score_documents, DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_GAMMA, DEFAULT_DELTA

app = FastAPI(
    title="Legal Precedent Search Engine API",
    description="A custom IR engine using Tries, Inverted Indexes, PageRank, and Composite Ranking."
)

# Global structures initialized on startup
inverted_index = InvertedIndex()
autocomplete_manager = AutocompleteManager()
citation_graph = CitationGraph()

# Precomputed metrics
pagerank_scores: Dict[str, float] = {}
direct_overrules: Dict[str, List[str]] = {}
caution_cases: Dict[str, List[str]] = {}

@app.on_event("startup")
def startup_event():
    print("Initializing Search Engine structures...")
    docs = get_mock_corpus()
    
    # 1. Build Inverted Index & Autocomplete
    for doc in docs:
        inverted_index.index_document(doc.doc_id, doc.opinion_text)
        autocomplete_manager.index_document(
            doc_id=doc.doc_id,
            case_name=doc.case_name,
            citation=doc.citation,
            judges=doc.judges,
            opinion_text=doc.opinion_text
        )
    
    # 2. Build Citation Graph
    citation_graph.build_graph(docs)
    
    # 3. Compute PageRank
    global pagerank_scores
    pagerank_scores = compute_pagerank(citation_graph)
    
    # 4. Detect overruled / bad law
    global direct_overrules, caution_cases
    direct_overrules, caution_cases = detect_overruled_cases(citation_graph)
    
    print(f"Startup complete. Loaded {len(docs)} documents.")

def extract_snippet(text: str, query_terms: List[str], window_words: int = 15) -> str:
    """Extracts a text window around query terms and wraps matches in html <mark> tags."""
    words = text.split()
    words_clean = [w.lower().strip(".,;:()[]\"'?") for w in words]
    
    stemmed_query_terms = {stem_word(t) for t in query_terms}
    
    match_indices = []
    for idx, word in enumerate(words_clean):
        if stem_word(word) in stemmed_query_terms:
            match_indices.append(idx)
            
    if not match_indices:
        return " ".join(words[:25]) + "..."
        
    # Build snippet window around the first match
    first_match = match_indices[0]
    start = max(0, first_match - window_words)
    end = min(len(words), first_match + window_words + 1)
    
    snippet_words = words[start:end]
    highlighted = []
    
    for word in snippet_words:
        w_clean = word.lower().strip(".,;:()[]\"'?")
        if stem_word(w_clean) in stemmed_query_terms:
            highlighted.append(f"<mark>{word}</mark>")
        else:
            highlighted.append(word)
            
    snippet = " ".join(highlighted)
    if start > 0:
        snippet = "... " + snippet
    if end < len(words):
        snippet = snippet + " ..."
        
    return snippet

@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Query string"),
    court: Optional[int] = Query(None, description="Filter by court tier (1=Supreme, 2=Appellate, 3=District)"),
    exclude_overruled: bool = Query(False, description="Exclude overruled cases"),
    alpha: float = Query(DEFAULT_ALPHA, description="BM25 Weight"),
    beta: float = Query(DEFAULT_BETA, description="PageRank Weight"),
    gamma: float = Query(DEFAULT_GAMMA, description="Court Tier Weight"),
    delta: float = Query(DEFAULT_DELTA, description="Recency Boost Weight")
):
    start_time = time.time()
    
    # 1. Parse and Tokenize Query
    q_trimmed = q.strip()
    is_phrase = q_trimmed.startswith('"') and q_trimmed.endswith('"')
    
    if is_phrase:
        # Extract phrase text and tokenize
        phrase_text = q_trimmed[1:-1]
        query_terms = tokenize(phrase_text)
        candidate_ids = inverted_index.phrase_query(query_terms)
    else:
        query_terms = tokenize(q)
        # Attempt Boolean AND intersection
        candidate_ids = inverted_index.intersect_postings(query_terms)
        
        # Fallback to Boolean OR if AND yields zero results
        if not candidate_ids and query_terms:
            union_set = set()
            for term in query_terms:
                for entry in inverted_index.get_postings(term):
                    union_set.add(entry.doc_id)
            candidate_ids = list(union_set)

    # If query is empty or yields no candidates
    if not candidate_ids:
        return SearchResponse(
            results=[],
            total_results=0,
            query_time_ms=round((time.time() - start_time) * 1000, 2)
        )

    # 2. Gather candidates information for scoring
    scoring_candidates = []
    for doc_id in candidate_ids:
        doc = citation_graph.doc_store.get(doc_id)
        if not doc:
            continue
            
        # Apply court filter if specified
        if court is not None and doc.court_level != court:
            continue
            
        bm25_score = compute_bm25(query_terms, doc_id, inverted_index)
        pr_score = pagerank_scores.get(doc_id, 0.0)
        is_overruled = doc_id in direct_overrules
        is_caution = doc_id in caution_cases
        
        scoring_candidates.append({
            "doc_id": doc_id,
            "bm25": bm25_score,
            "pagerank": pr_score,
            "court_level": doc.court_level,
            "date_decided": doc.date_decided,
            "is_overruled": is_overruled,
            "is_caution": is_caution
        })

    # 3. Compute Composite Scores
    scored_list = score_documents(
        candidates=scoring_candidates,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        delta=delta,
        exclude_overruled=exclude_overruled
    )

    # 4. Map back to Case Document metadata & build snippets
    results = []
    for item in scored_list:
        doc_id = item["doc_id"]
        doc = citation_graph.doc_store[doc_id]
        
        snippet = extract_snippet(doc.opinion_text, query_terms)
        
        results.append(SearchResult(
            doc_id=doc_id,
            case_name=doc.case_name,
            citation=doc.citation,
            court=doc.court,
            court_level=doc.court_level,
            date_decided=doc.date_decided,
            is_overruled=item["is_overruled"],
            is_caution=item["is_caution"],
            overruled_by=direct_overrules.get(doc_id, []),
            score=item["score"],
            score_breakdown=item["score_breakdown"],
            snippet=snippet
        ))

    query_time_ms = round((time.time() - start_time) * 1000, 2)
    return SearchResponse(
        results=results,
        total_results=len(results),
        query_time_ms=query_time_ms
    )

@app.get("/api/suggest")
def suggest(q: str = Query(..., min_length=1)):
    """Prefix-autocomplete suggestions categorized by match type."""
    return autocomplete_manager.suggest(q)

@app.get("/api/case/{doc_id}")
def get_case(doc_id: str):
    """Retrieves full case details along with its local citation graph node context."""
    doc = citation_graph.doc_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Case not found")

    # Construct surrounding citation network for the UI graph visualizer
    citations_in_details = []
    incoming_edges = citation_graph.reverse_adj.get(doc_id, [])
    for citing, w, treatment in incoming_edges:
        citing_doc = citation_graph.doc_store.get(citing)
        if citing_doc:
            citations_in_details.append({
                "doc_id": citing,
                "case_name": citing_doc.case_name,
                "citation": citing_doc.citation,
                "treatment": treatment,
                "court_level": citing_doc.court_level
            })

    citations_out_details = []
    outgoing_edges = citation_graph.adj.get(doc_id, [])
    for cited, w, treatment in outgoing_edges:
        cited_doc = citation_graph.doc_store.get(cited)
        if cited_doc:
            citations_out_details.append({
                "doc_id": cited,
                "case_name": cited_doc.case_name,
                "citation": cited_doc.citation,
                "treatment": treatment,
                "court_level": cited_doc.court_level
            })

    return {
        "metadata": doc,
        "is_overruled": doc_id in direct_overrules,
        "is_caution": doc_id in caution_cases,
        "overruled_by": direct_overrules.get(doc_id, []),
        "cautions_relied_on": caution_cases.get(doc_id, []),
        "pagerank": round(pagerank_scores.get(doc_id, 0.0), 6),
        "citations_in": citations_in_details,
        "citations_out": citations_out_details
    }

@app.get("/api/stats")
def get_stats():
    """Retrieve corpus, index, and authority metrics."""
    pr_values = list(pagerank_scores.values())
    return {
        "total_documents": len(citation_graph.doc_store),
        "vocabulary_size": len(inverted_index.index),
        "overruled_count": len(direct_overrules),
        "caution_count": len(caution_cases),
        "pagerank_min": round(min(pr_values), 6) if pr_values else 0,
        "pagerank_max": round(max(pr_values), 6) if pr_values else 0
    }

# Serve Frontend static directory
# If static folder exists, mount it
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", response_class=FileResponse)
    def read_root():
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    @app.get("/", response_class=HTMLResponse)
    def read_root_fallback():
        return """
        <html>
            <head><title>Search Engine Backend</title></head>
            <body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
                <h1>Search Engine Backend is Running</h1>
                <p>Create the 'static/' folder in the workspace to see the Web UI.</p>
                <p>Access the API Docs: <a href="/docs">/docs</a></p>
            </body>
        </html>
        """
