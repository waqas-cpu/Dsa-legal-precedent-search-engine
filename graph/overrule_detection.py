from typing import Dict, List, Set, Tuple
from graph.citation_graph import CitationGraph

def detect_overruled_cases(graph: CitationGraph) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Traverses the citation graph to detect overruled cases and cases that require caution.
    
    Returns:
        direct_overrules: Dict[doc_id, List[overruled_by_doc_ids]]
        caution_cases: Dict[doc_id, List[overruled_cited_doc_ids]] - cases relying on overruled law
    """
    direct_overrules: Dict[str, List[str]] = {}
    caution_cases: Dict[str, List[str]] = {}

    # 1. Detect Direct Overrules
    # We look at all nodes in the graph
    for doc_id in graph.nodes:
        # Check reverse adjacency list to find who cites this doc_id
        incoming_edges = graph.reverse_adj.get(doc_id, [])
        for citing_id, weight, treatment in incoming_edges:
            if treatment == "overruled":
                direct_overrules.setdefault(doc_id, []).append(citing_id)

    # 2. Detect Transitive Cautions
    # If case A relies on ('followed' or 'cited_generally') case B, and case B is directly overruled,
    # then case A should receive a caution flag.
    for doc_id in graph.nodes:
        # If this case is already directly overruled, it doesn't need a transitive caution flag (it's already dead law)
        if doc_id in direct_overrules:
            continue

        # Look at the cases cited by doc_id
        outgoing_edges = graph.adj.get(doc_id, [])
        for cited_id, weight, treatment in outgoing_edges:
            # If the cited case is in direct_overrules, and we followed or cited it
            if cited_id in direct_overrules:
                if treatment in {"followed", "cited_generally"}:
                    current_cautions = caution_cases.setdefault(doc_id, [])
                    if cited_id not in current_cautions:
                        current_cautions.append(cited_id)

    return direct_overrules, caution_cases
