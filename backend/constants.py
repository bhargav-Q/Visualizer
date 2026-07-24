"""
Centralized Backend Domain Constants & Keyword Sets
"""

from enum import Enum

# Domain protection keyword set for numeric financial/tabular triage
QUANTITATIVE_SIGNALS = {
    'payroll', 'losses', 'premium', 'claim', 'amount', 'revenue',
    'cost', 'total', 'ratio', 'expenditure', 'balance', 'fee',
    'price', 'rate', 'xmod', 'sales', 'profit', 'margin', 'asset', 'liability'
}

# Qualitative Document Domain Classification Categories
class DocumentDomain(str, Enum):
    INSURANCE_FINANCIAL = "Insurance / Financial Submission"
    CURRICULUM_SYLLABUS = "Curriculum / Syllabus"
    BUSINESS_OUTLINE = "Business Document Outline"

# English Stopwords Set for Keyword Scoring
ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "isn't", "it", "its", "itself", "just", "me", "more", "most", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "our", "ours",
    "ourselves", "out", "over", "own", "same", "she", "should", "shouldn't", "so", "some", "such",
    "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "were", "weren't", "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would",
    "wouldn't", "you", "your", "yours", "yourself", "yourselves", "page", "total", "date", "null", "none"
}

# Parsing Noise Suppression Thresholds
MIN_TOPIC_TITLE_LEN = 3
MIN_KEYWORD_MATCH_LEN = 3
