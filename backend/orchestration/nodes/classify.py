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


def build_classify_node():
    def classify(state: ConversationState) -> dict:
        query = state.get("query", "").strip()
        if not query:
            return {"intent": "greeting", "next_node": "respond_greeting"}

        for pattern in GREETING_PATTERNS:
            if pattern.match(query):
                logger.debug("Classified as greeting: '%s' matched %s", query[:40], pattern.pattern)
                return {"intent": "greeting", "next_node": "respond_greeting"}

        logger.debug("Classified as support: '%s'", query[:40])
        return {"intent": "support", "next_node": "retrieve"}

    return classify
