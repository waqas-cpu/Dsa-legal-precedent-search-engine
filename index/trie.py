import re
from typing import List, Set, Dict, Any, Optional

class TrieNode:
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end_of_term: bool = False
        self.doc_ids: Set[str] = set()
        self.term_frequency: int = 0
        self.canonical_term: Optional[str] = None  # Stores the display name (e.g. original citation or case name)

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, term: str, doc_id: str, canonical: Optional[str] = None):
        """Inserts a term into the trie, associated with a doc_id."""
        node = self.root
        # Use canonical if provided, otherwise the term itself
        display_term = canonical if canonical is not None else term
        
        for ch in term.lower():
            node = node.children.setdefault(ch, TrieNode())
            
        node.is_end_of_term = True
        node.doc_ids.add(doc_id)
        node.term_frequency += 1
        node.canonical_term = display_term

    def _walk(self, prefix: str) -> Optional[TrieNode]:
        node = self.root
        for ch in prefix.lower():
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def autocomplete(self, prefix: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Returns top k completions starting with prefix.
        Each completion is represented by a dictionary:
        { "term": canonical_term, "doc_ids": list_of_doc_ids, "frequency": freq }
        """
        node = self._walk(prefix)
        if node is None:
            return []
        
        results: List[TrieNode] = []
        self._collect(node, results)
        
        # Sort by frequency descending, then alphabetically by canonical term
        results.sort(key=lambda x: (-x.term_frequency, x.canonical_term or ""))
        
        output = []
        for r in results[:k]:
            output.append({
                "term": r.canonical_term or "",
                "doc_ids": list(r.doc_ids),
                "frequency": r.term_frequency
            })
        return output

    def _collect(self, node: TrieNode, out: List[TrieNode]):
        if node.is_end_of_term:
            out.append(node)
        for child in node.children.values():
            self._collect(child, out)


def normalize_citation(citation: str) -> str:
    """
    Normalizes a citation to accelerate matching.
    e.g., '384 U.S. 436' -> '384us436'
    """
    return re.sub(r"[^a-zA-Z0-9]", "", citation).lower()


class AutocompleteManager:
    def __init__(self):
        self.case_names_trie = Trie()
        self.citations_trie = Trie()
        self.judges_trie = Trie()
        self.legal_terms_trie = Trie()

    def index_document(self, doc_id: str, case_name: str, citation: str, judges: List[str], opinion_text: str):
        # Index Case Name
        # We index the full name and also parts of the name (e.g. "Miranda v. Arizona" allows searching "Miranda" or "Arizona")
        self.case_names_trie.insert(case_name, doc_id, case_name)
        parts = re.split(r"\s+v\.\s+|\s+", case_name)
        for part in parts:
            part_cleaned = re.sub(r"[^\w]", "", part)
            if len(part_cleaned) > 2 and part_cleaned.lower() not in {"vs", "and", "the", "for", "in"}:
                self.case_names_trie.insert(part_cleaned, doc_id, case_name)

        # Index Citation
        normalized_cit = normalize_citation(citation)
        self.citations_trie.insert(normalized_cit, doc_id, citation)
        # Also index starting with the reporter name if it starts with numbers (e.g. "384 U.S. 436" -> also "U.S.")
        cit_match = re.search(r"\d+\s+([a-zA-Z\.\s]+)\s+\d+", citation)
        if cit_match:
            reporter = cit_match.group(1).strip()
            self.citations_trie.insert(normalize_citation(reporter), doc_id, citation)

        # Index Judges
        for judge in judges:
            # Index full judge name, and just the surname
            self.judges_trie.insert(judge, doc_id, judge)
            surname = judge.split(",")[0].strip()
            if surname:
                self.judges_trie.insert(surname, doc_id, judge)

        # Index terms of art
        # We can extract some legal phrases or high frequency nouns from opinion text as 'terms of art'
        # For simplicity, we seed a small set of terms of art if they occur in the text
        terms_of_art = [
            "habeas corpus", "due process", "equal protection", "judicial review", 
            "de novo", "certiorari", "stare decisis", "mandamus", "administrative law",
            "self-incrimination", "exclusionary rule", "assistance of counsel", "sovereign immunity"
        ]
        opinion_lower = opinion_text.lower()
        for term in terms_of_art:
            if term in opinion_lower:
                self.legal_terms_trie.insert(term, doc_id, term)

    def suggest(self, prefix: str, k: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Queries all tries and returns categorized autocomplete suggestions."""
        # For citations, we normalize the query prefix
        norm_prefix = normalize_citation(prefix)
        
        return {
            "case_names": self.case_names_trie.autocomplete(prefix, k),
            "citations": self.citations_trie.autocomplete(norm_prefix, k),
            "judges": self.judges_trie.autocomplete(prefix, k),
            "legal_terms": self.legal_terms_trie.autocomplete(prefix, k)
        }
