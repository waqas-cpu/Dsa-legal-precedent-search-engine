from typing import List, Dict, Tuple, Set
from ingestion.schema import CaseDocument

TREATMENT_WEIGHT = {
    "followed": 1.0,
    "cited_generally": 0.6,
    "distinguished": 0.3,
    "criticized": 0.2,
    "overruled": -1.0,  # Negative weight, handled separately during propagation
}

class CitationGraph:
    def __init__(self):
        # citing -> list of (cited, weight, treatment)
        self.adj: Dict[str, List[Tuple[str, float, str]]] = {}
        # cited -> list of (citing, weight, treatment)
        self.reverse_adj: Dict[str, List[Tuple[str, float, str]]] = {}
        # Store all node ids
        self.nodes: Set[str] = set()
        # Map to store actual case documents for quick reference
        self.doc_store: Dict[str, CaseDocument] = {}

    def add_node(self, node_id: str, doc: CaseDocument):
        self.nodes.add(node_id)
        self.doc_store[node_id] = doc

    def add_edge(self, citing_id: str, cited_id: str, treatment: str):
        w = TREATMENT_WEIGHT.get(treatment, 0.6)
        
        self.adj.setdefault(citing_id, []).append((cited_id, w, treatment))
        self.reverse_adj.setdefault(cited_id, []).append((citing_id, w, treatment))
        
        self.nodes.add(citing_id)
        self.nodes.add(cited_id)

    def build_graph(self, documents: List[CaseDocument]):
        """Populates nodes and citation edges from CaseDocument list."""
        # First pass: add all documents as nodes
        for doc in documents:
            self.add_node(doc.doc_id, doc)

        # Second pass: construct directed edges
        for doc in documents:
            citing_id = doc.doc_id
            for cited_id in doc.citations_out:
                # Determine treatment type based on schema indicators
                treatment = "cited_generally"
                
                # Check citing document's structure/text indicators
                # or cited document's treatment signals
                cited_doc = self.doc_store.get(cited_id)
                
                if cited_doc:
                    ts = cited_doc.treatment_signals
                    if citing_id in ts.get("overruled_by", []):
                        treatment = "overruled"
                    elif citing_id in ts.get("followed_by", []):
                        treatment = "followed"
                    elif citing_id in ts.get("distinguished_by", []):
                        treatment = "distinguished"
                    elif citing_id in ts.get("criticized_by", []):
                        treatment = "criticized"

                self.add_edge(citing_id, cited_id, treatment)
