import math
from typing import List
from index.inverted_index import InvertedIndex

def compute_bm25(
    query_terms: List[str],
    doc_id: str,
    index: InvertedIndex,
    k1: float = 1.5,
    b: float = 0.75
) -> float:
    """
    Computes the BM25 relevance score for a document and a pre-tokenized query.
    Clips IDF to prevent negative values for very common terms.
    """
    score = 0.0
    N = index.N
    if N == 0:
        return 0.0

    doc_lengths = index.doc_lengths
    avg_doc_length = index.avg_doc_length
    
    # If the document has no tokens indexed
    if doc_id not in doc_lengths or doc_lengths[doc_id] == 0:
        return 0.0

    dl = doc_lengths[doc_id]

    for term in query_terms:
        postings = index.get_postings(term)
        # Find if this doc contains the term
        entry = next((p for p in postings if p.doc_id == doc_id), None)
        if not entry:
            continue

        df = len(postings)
        
        # Calculate IDF. Clip at 0 (or a tiny positive value) to prevent negative IDFs for extremely common terms
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
        idf = max(1e-5, idf)

        tf = entry.term_freq
        
        # BM25 denominator term frequency saturation and length normalization
        denom = tf + k1 * (1.0 - b + b * (dl / avg_doc_length))
        
        # Add term contribution
        score += idf * (tf * (k1 + 1.0)) / denom

    return score
