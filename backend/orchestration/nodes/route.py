from backend.orchestration.state import ConversationState


INTENT_KEYWORDS: dict[str, list[str]] = {
    "refund": ["return", "refund", "money back"],
    "shipping": ["shipping", "delivery"],
    "warranty": ["warrant"],
    "password": ["password", "reset"],
    "upgrade": ["upgrade", "downgrade"],
    "cancellation": ["cancel", "close account", "delete account"],
    "billing": ["bill", "payment", "invoice"],
    "trial": ["trial", "free"],
    "privacy": ["privacy", "gdpr", "data"],
    "contact": ["contact", "support", "phone"],
    "pricing": ["price", "cost", "pricing"],
    "licensing": ["license"],
    "sla": ["sla", "uptime"],
    "nonprofit": ["nonprofit", "non-profit", "discount"],
}


def build_route_node():
    def route(state: ConversationState) -> dict:
        query = state.get("query", "").lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                return {"intent": intent, "next_node": intent}
        return {"intent": "general", "next_node": "general"}
    return route
