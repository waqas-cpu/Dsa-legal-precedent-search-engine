import re
from typing import List, Set

# Standard and legal domain stopwords
# We keep words like 'plaintiff', 'defendant', 'court' searchable, but remove high-frequency function words.
STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves",
    # Legal formalisms with low semantic query value
    "herein", "thereto", "wherefore", "hereinafter", "aforesaid", "said", "heretofore", "thereunder"
}

def clean_text(text: str) -> str:
    """Lowercase and normalize whitespaces, while preserving paragraph (§, ¶) symbols."""
    text = text.lower()
    # Replace non-alphanumeric, non-section signs with spaces, preserving hyphens and underscores inside words
    text = re.sub(r"[^\w\s§¶\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def stem_word(word: str) -> str:
    """
    A lightweight, robust rule-based English stemmer.
    Handles plurals, past tense, gerunds, and common legal suffixes.
    """
    if len(word) <= 2:
        return word

    # Step 1: Plurals and basic suffixes
    if word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("ies"):
        # e.g., parties -> parti, categories -> categori
        word = word[:-3] + "i"
    elif word.endswith("ss"):
        pass
    elif word.endswith("s") and not word.endswith("us") and not word.endswith("is") and not word.endswith("as"):
        # Avoid stemming words like status, basis, corpus, gas
        word = word[:-1]

    # Step 2: Gerunds and Past Tense
    if word.endswith("eed"):
        if len(word) > 4:
            word = word[:-1] # e.g. agreed -> agree
    elif word.endswith("ing"):
        word = word[:-3]
        if len(word) > 1 and word[-1] == word[-2] and word[-1] not in "lsz":
            word = word[:-1] # double consonant cleanup, e.g., hopping -> hop
    elif word.endswith("ed"):
        word = word[:-2]
        if len(word) > 1 and word[-1] == word[-2] and word[-1] not in "lsz":
            word = word[:-1]
        elif word.endswith("i"):
            word = word[:-1] + "y"  # e.g. denied -> deny

    # Step 3: Derivational suffixes common in legal terms
    if word.endswith("ational"):
        word = word[:-7] + "ate" # constitutional -> constitution
    elif word.endswith("tional"):
        word = word[:-6] + "tion" # protectional -> protection
    elif word.endswith("tionality"):
        word = word[:-9] + "tion"
    elif word.endswith("alism"):
        word = word[:-5] + "al"
    elif word.endswith("ality"):
        word = word[:-5] + "al" # equality -> equal
    elif word.endswith("ibility"):
        word = word[:-7] + "ible"
    elif word.endswith("ability"):
        word = word[:-7] + "able" # culpability -> culpable
    elif word.endswith("ment") and len(word) > 6:
        word = word[:-4] # amendment -> amend, detriment -> detri
    elif word.endswith("ness"):
        word = word[:-4]
    elif word.endswith("fully"):
        word = word[:-4] # lawfully -> law
    elif word.endswith("ly"):
        word = word[:-2] # inherently -> inherent

    # Step 4: Y to I
    if word.endswith("y") and len(word) > 3:
        # Check if there is a vowel before y
        if word[-2] not in "aeiou":
            word = word[:-1] + "i" # custody -> custodi, party -> parti

    # Step 5: Strip trailing e (standard in Porter stemming Step 5a)
    if word.endswith("e") and not word.endswith("ee") and len(word) > 4:
        word = word[:-1]

    return word


def tokenize(text: str) -> List[str]:
    """Tokenizes text, strips stopwords, and returns a list of stemmed tokens."""
    cleaned = clean_text(text)
    raw_tokens = cleaned.split(" ")
    tokens = []
    for t in raw_tokens:
        if not t:
            continue
        if t in STOPWORDS:
            continue
        stemmed = stem_word(t)
        if stemmed:
            tokens.append(stemmed)
    return tokens
