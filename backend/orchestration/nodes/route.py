import re
import logging

from backend.orchestration.state import ConversationState

logger = logging.getLogger("gigacorp.route")

INTENT_KEYWORDS: dict[str, list[str]] = {
    "order_status": ["track order", "where is my order", "order status", "my order", "tracking"],
    "loyalty": ["loyalty", "points", "rewards", "loyalty tier", "my tier", "my points"],
    "refund": ["return", "refund", "money back"],
    "shipping": ["shipping", "delivery", "ship"],
    "warranty": ["warrant"],
    "password": ["password", "reset"],
    "upgrade": ["upgrade", "downgrade"],
    "cancellation": ["cancel", "close account", "delete account"],
    "billing": ["bill", "payment", "invoice", "subscription"],
    "trial": ["trial", "free"],
    "privacy": ["privacy", "gdpr", "data"],
    "contact": ["contact", "support", "phone"],
    "pricing": ["price", "cost", "pricing", "how much"],
    "licensing": ["license"],
    "sla": ["sla", "uptime"],
    "nonprofit": ["nonprofit", "non-profit", "discount"],
}

PRONOUN_RE = re.compile(r'\b(it|there|they|that|this|these|those|them|here)\b', re.I)

FOLLOW_UP_KEYWORDS: dict[str, list[str]] = {
    "refund": ["return", "refund", "money"],
    "shipping": ["ship", "delivery", "track", "order", "cost", "price", "fee", "rate"],
    "pricing": ["cost", "price", "pricing", "fee", "much", "how much"],
    "billing": ["bill", "payment", "invoice", "charge", "subscription"],
    "warranty": ["warrant", "repair", "replace"],
    "cancellation": ["cancel", "close"],
    "upgrade": ["upgrade", "downgrade"],
    "trial": ["trial", "free"],
    "contact": ["contact", "support", "phone", "email"],
    "order_status": ["track", "order", "status", "delivery"],
    "loyalty": ["points", "loyalty", "tier", "rewards"],
}


def _find_matching_intents(query: str) -> list[str]:
    q = query.lower()
    matched = []
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            matched.append(intent)
    return matched


def _find_last_intent_in_history(history: str) -> str | None:
    if not history:
        return None
    lines = history.strip().split("\n")
    for line in reversed(lines):
        lower = line.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return intent
    return None


def _find_follow_up_match(query: str, history: str) -> str | None:
    q = query.lower()

    # Find all intents that match keywords in the current query
    matched_intents = []
    for intent, keywords in FOLLOW_UP_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            matched_intents.append(intent)

    if not matched_intents:
        return None

    # Single match — use it
    if len(matched_intents) == 1:
        return matched_intents[0]

    # Multiple matches — prefer the one that matches the last intent from history
    last_intent = _find_last_intent_in_history(history)
    if last_intent and last_intent in matched_intents:
        logger.debug("Route: disambiguated via history -> %s", last_intent)
        return last_intent

    return matched_intents[0]


def build_route_node():
    def route(state: ConversationState) -> dict:
        query = state.get("query", "").lower()
        history = state.get("history_str", "") or ""

        has_pronoun = bool(PRONOUN_RE.search(query))

        # Follow-up with pronoun: use context-aware resolution
        if has_pronoun:
            follow_up = _find_follow_up_match(query, history)
            if follow_up:
                logger.debug("Route: follow-up '%s' -> %s", query[:30], follow_up)
                return {"intent": follow_up, "next_node": follow_up}

            # No keyword match in follow-up — defer to history context
            last_intent = _find_last_intent_in_history(history)
            if last_intent:
                logger.debug("Route: pronoun context fallback -> %s", last_intent)
                return {"intent": last_intent, "next_node": last_intent}

            logger.debug("Route: pronoun but no context -> general")
            return {"intent": "general", "next_node": "general"}

        # Direct keyword match (no pronoun)
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                logger.debug("Route: direct match '%s' -> %s", query[:30], intent)
                return {"intent": intent, "next_node": intent}

        logger.debug("Route: no match, default -> general")
        return {"intent": "general", "next_node": "general"}

    return route
