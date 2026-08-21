import datetime
from typing import Dict, Any, List

# Default weights for the composite scoring function
DEFAULT_ALPHA = 0.5   # Textual BM25 weight
DEFAULT_BETA = 0.25   # PageRank authority weight
DEFAULT_GAMMA = 0.15  # Court level tier weight
DEFAULT_DELTA = 0.10  # Recency boost weight

COURT_TIER_WEIGHTS = {
    1: 1.0,   # Supreme Court
    2: 0.75,  # Circuit Court
    3: 0.5,   # District Court
    4: 0.25   # Administrative
}

def calculate_recency_boost(date_str: str) -> float:
    """
    Computes a recency boost score between 0.0 and 1.0 using hyperbolic decay.
    Boost = 1 / (1 + 0.02 * age_in_years)
    """
    try:
        dec_year = int(date_str.split("-")[0])
        current_year = datetime.datetime.now().year
        age = max(0, current_year - dec_year)
        return 1.0 / (1.0 + 0.02 * age)
    except Exception:
        return 0.5

def score_documents(
    candidates: List[Dict[str, Any]],
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    gamma: float = DEFAULT_GAMMA,
    delta: float = DEFAULT_DELTA,
    exclude_overruled: bool = False
) -> List[Dict[str, Any]]:
    """
    Applies composite scoring and normalization across the candidate set.
    Normalizes BM25 and PageRank to [0, 1] relative to the candidate set.
    
    Each candidate dictionary should contain:
    - doc_id: str
    - bm25: float
    - pagerank: float
    - court_level: int
    - date_decided: str
    - is_overruled: bool
    """
    if not candidates:
        return []

    # Extract BM25 and PageRank scores to find min/max for normalization
    bm25_scores = [c["bm25"] for c in candidates]
    pr_scores = [c["pagerank"] for c in candidates]

    min_bm25, max_bm25 = min(bm25_scores), max(bm25_scores)
    min_pr, max_pr = min(pr_scores), max(pr_scores)

    scored_results = []

    for c in candidates:
        doc_id = c["doc_id"]
        is_overruled = c["is_overruled"]
        is_caution = c.get("is_caution", False)

        # 1. Normalize BM25
        bm25_range = max_bm25 - min_bm25
        bm25_norm = (c["bm25"] - min_bm25) / bm25_range if bm25_range > 0 else (1.0 if max_bm25 > 0 else 0.0)

        # 2. Normalize PageRank
        pr_range = max_pr - min_pr
        pr_norm = (c["pagerank"] - min_pr) / pr_range if pr_range > 0 else (1.0 if max_pr > 0 else 0.0)

        # 3. Court tier weight
        court_weight = COURT_TIER_WEIGHTS.get(c["court_level"], 0.25)

        # 4. Recency boost
        recency_boost = calculate_recency_boost(c["date_decided"])

        # Calculate composite score
        composite_score = (
            alpha * bm25_norm +
            beta * pr_norm +
            gamma * court_weight +
            delta * recency_boost
        )

        score_breakdown = {
            "bm25_raw": c["bm25"],
            "bm25_norm": bm25_norm,
            "pagerank_raw": c["pagerank"],
            "pagerank_norm": pr_norm,
            "court_weight": court_weight,
            "recency_boost": recency_boost
        }

        # Apply overruling constraints
        if is_overruled:
            if exclude_overruled:
                continue
            # If not excluded, penalize heavily so they sink to the bottom
            composite_score = 0.01 * composite_score

        scored_results.append({
            "doc_id": doc_id,
            "score": round(composite_score, 4),
            "score_breakdown": score_breakdown,
            "is_overruled": is_overruled,
            "is_caution": is_caution
        })

    # Sort candidates by final score descending
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    return scored_results
