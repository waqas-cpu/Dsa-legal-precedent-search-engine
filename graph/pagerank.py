from typing import Dict
from graph.citation_graph import CitationGraph

# Map court_level to its weight multiplier for PageRank contribution
# Supreme Court cases should carry more weight than lower court decisions
COURT_AUTHORITY_WEIGHT = {
    1: 1.0,   # Supreme Court
    2: 0.75,  # Circuit / Appellate Court
    3: 0.5,   # District / Trial Court
    4: 0.25   # Administrative / Tribunal
}

def compute_pagerank(
    graph: CitationGraph, 
    d: float = 0.85, 
    iterations: int = 50, 
    tol: float = 1e-6
) -> Dict[str, float]:
    """
    Computes a weighted, court-adjusted PageRank score for each case.
    Dangling nodes are handled by distributing their residual PageRank.
    """
    nodes = list(graph.nodes)
    N = len(nodes)
    if N == 0:
        return {}

    # Initialize scores uniformly
    score = {node: 1.0 / N for node in nodes}

    for _ in range(iterations):
        # Base rank due to teleportation
        new_score = {node: (1.0 - d) / N for node in nodes}
        
        # Track residual score from dangling nodes (nodes with no positive out-links)
        dangling_sum = 0.0

        for citing in nodes:
            # Get edges originating from this citing node
            edges = graph.adj.get(citing, [])
            positive_edges = [(cited, w) for cited, w, treatment in edges if w > 0]
            
            # Retrieve the court level of the citing case to weight its influence
            citing_doc = graph.doc_store.get(citing)
            court_level = citing_doc.court_level if citing_doc else 3
            court_mult = COURT_AUTHORITY_WEIGHT.get(court_level, 0.5)
            
            # Adjusted score contribution from this node
            propagate_score = score[citing] * court_mult
            
            if not positive_edges:
                # Dangling node - accumulates score to distribute to everyone
                dangling_sum += propagate_score
            else:
                # Sum weights of positive edges to normalize
                out_weight_sum = sum(w for _, w in positive_edges)
                for cited, w in positive_edges:
                    # Distribute score proportionally to edge weights
                    new_score[cited] += d * propagate_score * (w / out_weight_sum)

        # Distribute dangling node score evenly
        if dangling_sum > 0:
            for node in nodes:
                new_score[node] += d * (dangling_sum / N)

        # Check for convergence
        delta = sum(abs(new_score[node] - score[node]) for node in nodes)
        score = new_score
        if delta < tol:
            break

    return score
