import unittest
from ingestion.schema import CaseDocument
from index.tokenizer import tokenize, stem_word, clean_text
from index.trie import Trie, AutocompleteManager, normalize_citation
from index.inverted_index import InvertedIndex
from graph.citation_graph import CitationGraph
from graph.pagerank import compute_pagerank
from graph.overrule_detection import detect_overruled_cases
from ranking.bm25 import compute_bm25
from ranking.composite_score import score_documents

class TestTokenizer(unittest.TestCase):
    def test_clean_text(self):
        text = "This is a section § 123 of the law, and paragraph ¶ 5."
        cleaned = clean_text(text)
        self.assertIn("§", cleaned)
        self.assertIn("¶", cleaned)
        self.assertNotIn(",", cleaned)
        self.assertNotIn(".", cleaned)

    def test_stemming(self):
        # Plural stems
        self.assertEqual(stem_word("parties"), "parti")
        self.assertEqual(stem_word("status"), "status")
        # Past tense / gerund stems
        self.assertEqual(stem_word("segregated"), "segregat")
        self.assertEqual(stem_word("abridging"), "abridg")
        self.assertEqual(stem_word("denied"), "deni")
        # Legal suffix stems
        self.assertEqual(stem_word("equality"), "equal")
        self.assertEqual(stem_word("culpability"), "culpabl")
        self.assertEqual(stem_word("amendment"), "amend")
        self.assertEqual(stem_word("inherently"), "inherent")

    def test_tokenizer(self):
        text = "We conclude that separate educational facilities are inherently unequal."
        tokens = tokenize(text)
        # Check stopwords removed (e.g. "we", "that", "are")
        self.assertNotIn("we", tokens)
        self.assertNotIn("that", tokens)
        # Check remaining terms are stemmed
        self.assertIn("conclud", tokens)
        self.assertIn("separat", tokens)
        self.assertIn("educat", tokens)
        self.assertIn("faciliti", tokens)
        self.assertIn("inherent", tokens)
        self.assertIn("unequal", tokens)

class TestTrie(unittest.TestCase):
    def test_trie_insert_and_autocomplete(self):
        trie = Trie()
        trie.insert("Miranda v. Arizona", "miranda", "Miranda v. Arizona")
        trie.insert("Marbury v. Madison", "marbury", "Marbury v. Madison")
        
        # Test exact match prefix
        results = trie.autocomplete("mir")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["term"], "Miranda v. Arizona")
        
        # Test case insensitivity
        results = trie.autocomplete("MAR")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["term"], "Marbury v. Madison")

    def test_citation_normalization(self):
        self.assertEqual(normalize_citation("384 U.S. 436"), "384us436")
        self.assertEqual(normalize_citation("384 US 436"), "384us436")

class TestInvertedIndex(unittest.TestCase):
    def setUp(self):
        self.index = InvertedIndex()
        self.index.index_document("doc1", "We conclude that separate facilities are inherently unequal.")
        self.index.index_document("doc2", "Separate educational facilities are equal under legal status.")
        self.index.index_document("doc3", "We have a constitutional right to due process of law.")

    def test_boolean_and(self):
        # both docs contain "separat" and "faciliti"
        results = self.index.intersect_postings(["separat", "faciliti"])
        self.assertEqual(set(results), {"doc1", "doc2"})

        # Only doc1 has "inherent"
        results = self.index.intersect_postings(["separat", "inherent"])
        self.assertEqual(results, ["doc1"])

    def test_phrase_query(self):
        # Test exact sequence
        results = self.index.phrase_query(["separat", "faciliti"]) # doc1: "separate facilities"
        self.assertEqual(results, ["doc1"])
        
        # Test reverse sequence (should fail)
        results = self.index.phrase_query(["faciliti", "separat"])
        self.assertEqual(results, [])

class TestCitationGraph(unittest.TestCase):
    def setUp(self):
        self.graph = CitationGraph()
        # Seed mock documents
        self.docA = CaseDocument(
            doc_id="caseA", case_name="Case A", citation="1 A 1", court="SC", court_level=1,
            jurisdiction="US", date_decided="1900-01-01", opinion_text="opinion text",
            citations_out=["caseB"], treatment_signals={"overruled_by": ["caseC"]}
        )
        self.docB = CaseDocument(
            doc_id="caseB", case_name="Case B", citation="2 B 2", court="SC", court_level=1,
            jurisdiction="US", date_decided="1910-01-01", opinion_text="opinion text citing",
            citations_out=[], treatment_signals={}
        )
        self.docC = CaseDocument(
            doc_id="caseC", case_name="Case C", citation="3 C 3", court="SC", court_level=1,
            jurisdiction="US", date_decided="1920-01-01", opinion_text="opinion text overruling",
            citations_out=["caseA"], treatment_signals={}
        )
        self.graph.build_graph([self.docA, self.docB, self.docC])

    def test_graph_building(self):
        # A cites B (generally)
        edges_A = self.graph.adj.get("caseA", [])
        self.assertTrue(any(cited == "caseB" and w == 0.6 for cited, w, t in edges_A))

        # C cites A and overrules A (B has treatment overruled_by C)
        # So edge from C -> A has overruled treatment
        edges_C = self.graph.adj.get("caseC", [])
        self.assertTrue(any(cited == "caseA" and t == "overruled" and w == -1.0 for cited, w, t in edges_C))

    def test_pagerank(self):
        pr = compute_pagerank(self.graph)
        self.assertEqual(len(pr), 3)
        # Every node should have some score, and they should sum to 1.0 (approx)
        self.assertAlmostEqual(sum(pr.values()), 1.0)

    def test_overrule_detection(self):
        # caseC cites caseA with treatment overruled. So caseA is directly overruled.
        direct, caution = detect_overruled_cases(self.graph)
        self.assertIn("caseA", direct)
        self.assertEqual(direct["caseA"], ["caseC"])
        
        # caseB is cited generally by caseA, which is overruled. 
        # But transitive caution check handles cases citing overruled cases, not vice versa.
        # Let's check: C cites A (overruled) with treatment overruled.
        # What if a Case D followed Case A?
        docD = CaseDocument(
            doc_id="caseD", case_name="Case D", citation="4 D 4", court="SC", court_level=1,
            jurisdiction="US", date_decided="1930-01-01", opinion_text="opinion text following",
            citations_out=["caseA"], treatment_signals={}
        )
        # Re-build graph
        graph = CitationGraph()
        # Mark caseA as overruled by caseC
        self.docA.treatment_signals = {"overruled_by": ["caseC"]}
        graph.build_graph([self.docA, self.docB, self.docC, docD])
        # Mark D as following A
        graph.add_edge("caseD", "caseA", "followed")
        
        direct, caution = detect_overruled_cases(graph)
        self.assertIn("caseA", direct)
        # caseD relies on overruled caseA (followed treatment), so D should receive caution
        self.assertIn("caseD", caution)
        self.assertEqual(caution["caseD"], ["caseA"])

if __name__ == "__main__":
    unittest.main()
