from typing import List, Dict, Set, Optional, Tuple
from index.tokenizer import tokenize

class PostingEntry:
    def __init__(self, doc_id: str):
        self.doc_id: str = doc_id
        self.term_freq: int = 0
        self.positions: List[int] = []

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "term_freq": self.term_freq,
            "positions": self.positions
        }

class InvertedIndex:
    def __init__(self):
        # term -> list[PostingEntry], sorted by doc_id
        self.index: Dict[str, List[PostingEntry]] = {}
        # doc_id -> number of tokens (length)
        self.doc_lengths: Dict[str, int] = {}
        # total number of documents
        self.N: int = 0
        # average document length in the corpus
        self.avg_doc_length: float = 0.0

    def index_document(self, doc_id: str, text: str):
        """Tokenizes text and updates index, postings, and lengths."""
        tokens = tokenize(text)
        if not tokens:
            return

        self.doc_lengths[doc_id] = len(tokens)
        self.N = len(self.doc_lengths)
        
        # Calculate term frequencies and positions within the document
        doc_term_data: Dict[str, List[int]] = {}
        for pos, term in enumerate(tokens):
            doc_term_data.setdefault(term, []).append(pos)

        # Update inverted index postings list
        for term, positions in doc_term_data.items():
            postings = self.index.setdefault(term, [])
            
            # Since we index doc by doc, the postings list remains sorted by doc_id
            entry = PostingEntry(doc_id)
            entry.term_freq = len(positions)
            entry.positions = positions
            postings.append(entry)

        # Recompute average document length
        total_len = sum(self.doc_lengths.values())
        self.avg_doc_length = total_len / self.N if self.N > 0 else 0.0

    def get_postings(self, term: str) -> List[PostingEntry]:
        return self.index.get(term, [])

    def get_doc_frequency(self, term: str) -> int:
        return len(self.index.get(term, []))

    def intersect_postings(self, terms: List[str]) -> List[str]:
        """
        Returns doc_ids containing ALL query terms (Boolean AND),
        efficiently intersecting using two-pointer merge over sorted doc_ids.
        """
        if not terms:
            return []
        
        # Retrieve postings lists for all terms
        postings_lists = [self.get_postings(term) for term in terms]
        if any(not p for p in postings_lists):
            return []  # One of the terms is not in the index

        # Sort lists by size to intersect the smallest first
        postings_lists.sort(key=len)
        
        # Start with the doc_ids of the smallest list
        candidate_ids = [p.doc_id for p in postings_lists[0]]
        
        for next_postings in postings_lists[1:]:
            intersected = []
            i, j = 0, 0
            n_candidates = len(candidate_ids)
            n_postings = len(next_postings)
            
            while i < n_candidates and j < n_postings:
                c_id = candidate_ids[i]
                p_id = next_postings[j].doc_id
                if c_id == p_id:
                    intersected.append(c_id)
                    i += 1
                    j += 1
                elif c_id < p_id:
                    i += 1
                else:
                    j += 1
            candidate_ids = intersected
            if not candidate_ids:
                break
                
        return candidate_ids

    def phrase_query(self, phrase_terms: List[str]) -> List[str]:
        """
        Retrieves documents that contain the terms in the phrase in order.
        Example: "beyond a reasonable doubt" -> stems must appear consecutively.
        """
        if not phrase_terms:
            return []
        if len(phrase_terms) == 1:
            return [p.doc_id for p in self.get_postings(phrase_terms[0])]

        # Step 1: Intersect doc_ids to find candidate docs containing all phrase terms
        candidate_docs = self.intersect_postings(phrase_terms)
        if not candidate_docs:
            return []

        result_docs = []
        
        # Step 2: For each candidate doc, perform positional intersection
        for doc_id in candidate_docs:
            # Gather positions list for each term in this document
            term_positions: List[List[int]] = []
            for term in phrase_terms:
                postings = self.get_postings(term)
                # Find the posting for this doc
                entry = next(p for p in postings if p.doc_id == doc_id)
                term_positions.append(entry.positions)
            
            # Check if there is a sequence of positions: pos, pos+1, pos+2, ...
            if self._has_consecutive_sequence(term_positions):
                result_docs.append(doc_id)

        return result_docs

    def _has_consecutive_sequence(self, lists: List[List[int]]) -> bool:
        """
        Checks if there is a consecutive sequence of numbers across the lists.
        lists[0] contains positions of term 1, lists[1] contains positions of term 2, etc.
        """
        # We start with the positions of the first term
        # and check if we can trace path to the last term
        for pos in lists[0]:
            match = True
            for offset in range(1, len(lists)):
                target_pos = pos + offset
                # Binary search or simple list lookup for target_pos in lists[offset]
                if not self._binary_search(lists[offset], target_pos):
                    match = False
                    break
            if match:
                return True
        return False

    def _binary_search(self, arr: List[int], target: int) -> bool:
        low = 0
        high = len(arr) - 1
        while low <= high:
            mid = (low + high) // 2
            if arr[mid] == target:
                return True
            elif arr[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
        return False
