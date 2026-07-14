import re
import logging

from backend.orchestration.state import ConversationState

logger = logging.getLogger("gigacorp.route")

INTENT_KEYWORDS: dict[str, list[str]] = {
    "ticket": ["support ticket", "my ticket", "ticket status", "open a ticket",
               "create a ticket", "raise a ticket", "ticket number", "submit a ticket",
               "file a complaint", "report a problem", "my support request"],
    "tracking": ["track package", "track my package", "where is my package",
                 "package location", "shipment status", "my shipment",
                 "tracking update", "where is my shipment", "when will it arrive",
                 "has my order shipped", "package tracking"],
    "invoice": ["invoice for", "get an invoice", "my invoice", "receipt for", "billing history"],
    "refund": ["refund", "money back"],
    "return_policy": ["return policy", "how to return", "return an item", "rma", "return label"],
    "exchange": ["exchange", "swap", "replace", "different product", "different size"],
    "order_status": ["track my order", "where is my order", "order status", "tracking number", "cancel my order", "cancel my pending", "what happened to ord", "order number"],
    "loyalty": ["loyalty", "points", "rewards", "loyalty tier", "my tier", "my points"],
    "shipping": ["shipping", "delivery", "ship"],
    "warranty": ["warrant"],
    "password": ["password", "reset"],
    "upgrade": ["upgrade", "downgrade"],
    "cancellation": ["cancel account", "close account", "delete account"],
    "billing": ["bill", "payment", "subscription"],
    "trial": ["trial", "free"],
    "privacy": ["privacy", "gdpr", "data"],
    "contact": ["contact", "support", "phone"],
    "pricing": ["price", "cost", "pricing", "how much"],
    "licensing": ["license"],
    "sla": ["sla", "uptime"],
    "nonprofit": ["nonprofit", "non-profit", "discount"],
}

PRONOUN_RE = re.compile(r'\b(it|there|they|that|this|these|those|them|here)\b', re.I)

TRACKING_RE = re.compile(
    r'\b(1Z\s*[A-Z0-9\s]{10,30}|'
    r'[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}\s*[0-9]{4}|'
    r'[0-9]{20,30}|'
    r'DHL[-\s][A-Z0-9]{6,15}|'
    r'[A-Z]{2}[0-9]{9}[A-Z]{2})\b',
    re.I
)

FOLLOW_UP_KEYWORDS: dict[str, list[str]] = {
    "refund": ["refund", "money"],
    "return_policy": ["return", "rma", "label"],
    "exchange": ["exchange", "swap", "replace"],
    "invoice": ["invoice", "receipt", "bill"],
    "shipping": ["ship", "delivery", "track", "cost", "fee", "rate"],
    "pricing": ["cost", "price", "pricing", "fee", "much", "how much"],
    "billing": ["bill", "payment", "invoice", "charge", "subscription"],
    "warranty": ["warrant", "repair", "replace"],
    "cancellation": ["cancel", "close"],
    "upgrade": ["upgrade", "downgrade"],
    "trial": ["trial", "free"],
    "contact": ["contact", "support", "phone", "email"],
    "order_status": ["track", "order", "status", "delivery"],
    "loyalty": ["points", "loyalty", "tier", "rewards"],
    "tracking": ["track", "package", "shipment", "delivery", "shipping update"],
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


def _resolve_intent_from_discussed(discussed: dict) -> str | None:
    if discussed.get("order") or discussed.get("tracking"):
        return "tracking"
    if discussed.get("ticket"):
        return "ticket"
    return None


def build_route_node():
    def route(state: ConversationState) -> dict:
        query = state.get("query", "").lower()
        history = state.get("history_str", "") or ""
        discussed = state.get("discussed_entities", {}) or {}

        has_pronoun = bool(PRONOUN_RE.search(query))

        # Follow-up with pronoun: use context-aware resolution
        if has_pronoun:
            follow_up = _find_follow_up_match(query, history)
            if follow_up:
                logger.debug("Route: follow-up '%s' -> %s", query[:30], follow_up)
                return {"intent": follow_up, "next_node": follow_up}

            discussed_intent = _resolve_intent_from_discussed(discussed)
            if discussed_intent:
                logger.debug("Route: pronoun resolved via discussed_entities -> %s", discussed_intent)
                return {"intent": discussed_intent, "next_node": discussed_intent}

            last_intent = _find_last_intent_in_history(history)
            if last_intent:
                logger.debug("Route: pronoun context fallback -> %s", last_intent)
                return {"intent": last_intent, "next_node": last_intent}

            logger.debug("Route: pronoun but no context -> general")
            return {"intent": "general", "next_node": "general"}

        # Check for tracking numbers in the query
        if TRACKING_RE.search(query):
            logger.debug("Route: tracking number detected -> tracking")
            return {"intent": "tracking", "next_node": "tracking"}

        # Direct keyword match (no pronoun)
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                logger.debug("Route: direct match '%s' -> %s", query[:30], intent)
                return {"intent": intent, "next_node": intent}

        # No keyword matched — check if discussed_entities can disambiguate
        discussed_intent = _resolve_intent_from_discussed(discussed)
        if discussed_intent:
            for kw in FOLLOW_UP_KEYWORDS.get(discussed_intent, []):
                if kw in query:
                    logger.debug("Route: discussed_entities fallback -> %s", discussed_intent)
                    return {"intent": discussed_intent, "next_node": discussed_intent}

        logger.debug("Route: no match, default -> general")
        return {"intent": "general", "next_node": "general"}

    return route
