"""Transparent account-scoped lexical retrieval for knowledge articles."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Iterable


STOPWORDS = {
    "a", "about", "after", "an", "and", "are", "as", "at", "be", "been",
    "but", "can", "could", "do", "does", "for", "from", "get", "has", "have",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "please",
    "that", "the", "this", "to", "was", "what", "when", "where", "with", "you",
}

SYNONYMS = {
    "signin": "login", "signon": "login", "logged": "login", "logging": "login",
    "pwd": "password", "passcode": "password", "moneyback": "refund",
    "reimbursement": "refund", "terminate": "cancel", "cancellation": "cancel",
    "booking": "reservation", "book": "reservation", "reserved": "reservation",
    "barcode": "qr", "crashing": "crash", "frozen": "freeze", "delete": "deletion",
    "disabled": "blocked", "charge": "billing", "charged": "billing",
    "notifications": "notification", "preferences": "preference",
    "reservations": "reservation", "experiences": "experience",
    "settings": "setting", "issues": "issue", "crashes": "crash",
    "freezes": "freeze", "emails": "email", "events": "event",
}


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    normalized = normalized.replace("money back", "moneyback").replace("sign in", "signin")
    raw = re.findall(r"[a-z0-9]+", normalized)
    return [SYNONYMS.get(token, token) for token in raw if token not in STOPWORDS and len(token) > 1]


def rank_articles(query: str, articles: Iterable[dict], limit: int = 3) -> list[dict]:
    """Return ranked copies with interpretable score/confidence fields."""

    article_list = list(articles)
    query_tokens = tokenize(query)
    if not query_tokens or not article_list:
        return []

    query_counts = Counter(query_tokens)
    doc_sets = [set(tokenize(f"{a['title']} {a.get('tags', '')} {a['content']}")) for a in article_list]
    document_frequency = Counter(token for tokens in doc_sets for token in tokens)
    scored: list[dict] = []

    for article, all_tokens in zip(article_list, doc_sets):
        title_tokens = Counter(tokenize(article["title"]))
        tag_tokens = Counter(tokenize(article.get("tags", "")))
        body_tokens = Counter(tokenize(article["content"]))
        weighted = 0.0
        matched: set[str] = set()
        for token, query_frequency in query_counts.items():
            if token not in all_tokens:
                continue
            matched.add(token)
            inverse_frequency = math.log((len(article_list) + 1) / (document_frequency[token] + 1)) + 1
            field_weight = 3.0 * title_tokens[token] + 2.4 * tag_tokens[token] + min(body_tokens[token], 3)
            weighted += query_frequency * inverse_frequency * field_weight

        coverage = len(matched) / len(set(query_tokens))
        phrase_bonus = 1.5 if any(phrase in query.lower() and phrase in article["content"].lower()
                                  for phrase in ("password reset", "qr code", "delete account", "sold out")) else 0.0
        raw_score = weighted + phrase_bonus
        confidence = min(0.99, coverage * 0.72 + min(raw_score / 25.0, 0.27)) if matched else 0.0
        if matched:
            scored.append({**article, "score": round(raw_score, 4), "confidence": round(confidence, 4),
                           "matched_terms": sorted(matched)})

    return sorted(scored, key=lambda item: (item["confidence"], item["score"]), reverse=True)[:limit]
