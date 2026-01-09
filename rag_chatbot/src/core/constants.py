"""
Constants and static configuration values for AM ROBOTS Chatbot.
"""

# Language mapping for multi-language support
LANGUAGE_MAP = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "es": "Spanish",
    "da": "Danish"
}

SUPPORTED_LANGUAGES = list(LANGUAGE_MAP.keys())

# AM ROBOTS Login URL for pricing
LOGIN_URL = "https://am-robots.com/login/"

# Keywords that indicate pricing queries
PRICE_KEYWORDS = [
    "price", "pricing", "cost", "how much", "euro", "eur", "€", "$", "dollar",
    "prix", "coût", "combien",  # French
    "preis", "kosten", "wieviel",  # German
    "prezzo", "costo", "quanto",  # Italian
    "precio", "coste", "cuánto",  # Spanish
    "pris", "koster", "hvor meget"  # Danish
]

# Harmful content patterns for input guardrails
HARMFUL_PATTERNS = [
    # Injection attempts
    "ignore previous", "ignore above", "disregard", "forget instructions",
    "new instructions", "override", "bypass", "jailbreak",
    # Harmful requests
    "hack", "exploit", "malware", "virus", "phishing",
    # Personal data extraction
    "credit card", "password", "social security", "bank account",
    # Inappropriate content
    "illegal", "weapon", "drug", "violence"
]

# Response limits
MAX_RESPONSE_LENGTH = 4000
MAX_CONTEXT_ITEMS = 10

# Product categories
PRODUCT_CATEGORIES = [
    "Robot mowers",
    "Boundary Cable", 
    "Standard Cable",
    "Garages",
    "Trackers",
    "Blades",
    "Connectors",
    "Tools",
    "Installation kits",
    "Pegs",
    "Accessories"
]

# Brand information
BRAND_NAME = "AM ROBOTS"
BRAND_WEBSITE = "https://am-robots.com/"
BRAND_EMAIL = "info@am-robots.com"
BRAND_PHONE = "+45 8140 1221"
BRAND_COUNTRY = "Denmark"
