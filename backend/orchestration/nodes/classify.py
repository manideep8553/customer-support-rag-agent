import re
import logging

from backend.orchestration.state import ConversationState

logger = logging.getLogger("gigacorp.classify")

GREETING_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(hi|hello|hey|greetings|howdy)\b", re.I),
    re.compile(r"^(good\s+)?(morning|afternoon|evening|day)\b", re.I),
    re.compile(r"^(thanks|thank\s+you|ty|appreciate\s+it|much\s+appreciated)\b", re.I),
    re.compile(r"^(bye|goodbye|see\s+you|talk\s+(later|soon)|have\s+a\s+good)\b", re.I),
    re.compile(r"^(how\s+are\s+you|how'?s\s+it\s+going|what'?s\s+up|sup)\b", re.I),
    re.compile(r"^(nice\s+to\s+meet\s+you|pleasure)\b", re.I),
    re.compile(r"^(sure|okay|ok|alright|got\s+it|understood|cool)\b", re.I),
    re.compile(r"^(yes|yeah|yep|no|nope|nah)\s*$", re.I),
    re.compile(r"^(that\s+)?(makes\s+sense|helpful|thanks|thank\s+you)", re.I),
]

# Intents that only need database customer data (no vector retrieval needed).
# Queries matching ONLY these patterns skip the vector store lookup.
CUSTOMER_INTENT_PATTERNS: dict[str, list[str]] = {
    "order_status": ["track my order", "where is my order", "order status",
                     "cancel my order", "what happened to ord", "order number",
                     "my order", "my orders"],
    "tracking": ["track package", "track my package", "where is my package",
                 "package location", "shipment status", "my shipment",
                 "tracking update", "where is my shipment", "when will it arrive",
                 "has my order shipped", "package tracking"],
    "ticket": ["support ticket", "my ticket", "ticket status", "open a ticket",
               "create a ticket", "raise a ticket", "ticket number", "submit a ticket",
               "file a complaint", "report a problem", "my support request"],
    "loyalty": ["loyalty", "points", "rewards", "loyalty tier", "my tier", "my points"],
    "invoice": ["invoice for", "get an invoice", "my invoice", "receipt for", "billing history"],
}

# Policy intents that need vector retrieval (RAG).
POLICY_INTENT_PATTERNS: dict[str, list[str]] = {
    "shipping": ["shipping", "delivery", "ship"],
    "refund": ["refund", "money back"],
    "return_policy": ["return policy", "how to return", "return an item", "rma", "return label"],
    "exchange": ["exchange", "swap", "replace", "different product", "different size"],
    "warranty": ["warrant"],
    "billing": ["bill", "payment", "subscription"],
    "pricing": ["price", "cost", "pricing", "how much"],
    "contact": ["contact", "support", "phone", "email support", "customer service", "talk to"],
    "password": ["password", "reset"],
    "upgrade": ["upgrade", "downgrade"],
    "cancellation": ["cancel account", "close account", "delete account"],
    "trial": ["trial", "free"],
    "privacy": ["privacy", "gdpr", "data"],
    "licensing": ["license"],
    "sla": ["sla", "uptime"],
    "nonprofit": ["nonprofit", "non-profit", "discount"],
}


def _match_any_keyword(query: str, patterns: dict[str, list[str]]) -> set[str]:
    q = query.lower()
    matched: set[str] = set()
    for intent, keywords in patterns.items():
        if any(kw in q for kw in keywords):
            matched.add(intent)
    return matched


def build_classify_node():
    def classify(state: ConversationState) -> dict:
        query = state.get("query", "").strip()
        if not query:
            return {"intent": "greeting", "next_node": "respond_greeting"}

        for pattern in GREETING_PATTERNS:
            if pattern.match(query):
                logger.debug("Classified as greeting: '%s' matched %s", query[:40], pattern.pattern)
                return {"intent": "greeting", "next_node": "respond_greeting"}

        # Determine data source: RAG (vector DB) or DB (customer data only)
        customer_intents = _match_any_keyword(query, CUSTOMER_INTENT_PATTERNS)
        policy_intents = _match_any_keyword(query, POLICY_INTENT_PATTERNS)

        if customer_intents and not policy_intents:
            logger.debug("Classified as DB-only query '%s' (customer intents: %s)", query[:40], customer_intents)
            return {"intent": "support", "next_node": "route"}

        if policy_intents:
            logger.debug("Classified as RAG-required query '%s' (policy intents: %s, customer intents: %s)",
                         query[:40], policy_intents, customer_intents)
        else:
            logger.debug("Classified as RAG-required query '%s' (no intents matched)", query[:40])

        return {"intent": "support", "next_node": "retrieve"}

    return classify
