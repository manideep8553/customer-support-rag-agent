import tiktoken
from typing import Optional

from backend.config import settings
from backend.rag.retriever import Retriever
from backend.memory.conversation import ConversationMemory


_SYSTEM_PROMPT = """You are GigaBot, an AI customer support representative for GigaCorp. You are helpful, professional, and concise.

Your responsibilities:
- Answer customer questions about GigaCorp products, policies, and services
- Provide accurate information based solely on the provided context
- Cite sources when referencing specific policies
- Be empathetic and professional in tone
- If you don't know the answer, say so honestly — do not make up information
- Keep responses focused and avoid unnecessary details

Company: GigaCorp — a global technology company offering cloud computing, AI analytics, and enterprise software.
"""


class RAGEngine:
    def __init__(self, retriever: Retriever, memory: ConversationMemory):
        self.retriever = retriever
        self.memory = memory
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def _format_context(self, results: list[dict]) -> str:
        if not results:
            return "No relevant documents found."

        sections = []
        for i, r in enumerate(results, 1):
            sections.append(f"[Source {i}] (Relevance: {r['score']:.2f})\n{r['content']}")
        return "\n\n".join(sections)

    def _build_prompt(self, query: str, context: str, history: str) -> str:
        return f"""{_SYSTEM_PROMPT}

{"=" * 60}
CONVERSATION HISTORY:
{history}
{"=" * 60}

RETRIEVED KNOWLEDGE:
{context}
{"=" * 60}

Current customer query: {query}

Instructions:
- Answer using ONLY the retrieved knowledge above.
- If the knowledge doesn't contain enough information, say: "I don't have enough information to answer that question. Please contact our support team at support@gigacorp.com for further assistance."
- Reference relevant sources when citing specific policies (e.g., "According to Section 3.2 of our Warranty Policy...").
- Keep answers concise and direct.

Answer:"""

    def query(self, session_id: str, message: str) -> dict:
        history = self.memory.get_history(session_id)
        results = self.retriever.retrieve(message)
        context = self._format_context(results)
        prompt = self._build_prompt(message, context, history)

        self.memory.add_turn(session_id, "user", message)
        self.memory.add_turn(session_id, "assistant", prompt)

        answer = self._simulate_inference(message, results, context, history)
        self.memory.add_turn(session_id, "assistant", answer)

        sources = [
            {
                "content": r["content"][:200],
                "score": r["score"],
                "source": r["source"],
            }
            for r in results
        ]

        return {"answer": answer, "sources": sources}

    def _simulate_inference(
        self, query: str, results: list[dict], context: str, history: str
    ) -> str:
        if not results:
            return (
                "I don't have enough information to answer that question. "
                "Please contact our support team at support@gigacorp.com for further assistance."
            )

        answer = self._generate_answer(query, results, context, history)
        return answer

    def _generate_answer(
        self, query: str, results: list[dict], context: str, history: str
    ) -> str:
        query_lower = query.lower()

        if "return" in query_lower or "refund" in query_lower or "money back" in query_lower:
            return self._answer_refund(query, results)
        if "shipping" in query_lower or "delivery" in query_lower:
            return self._answer_shipping(query, results)
        if "warrant" in query_lower:
            return self._answer_warranty(query, results)
        if "password" in query_lower or "reset" in query_lower:
            return self._answer_password(query, results)
        if "upgrade" in query_lower or "downgrade" in query_lower:
            return self._answer_upgrade(query, results)
        if "cancel" in query_lower or "close" in query_lower or "delete" in query_lower:
            return self._answer_cancellation(query, results)
        if "bill" in query_lower or "payment" in query_lower or "invoice" in query_lower:
            return self._answer_billing(query, results)
        if "trial" in query_lower or "free" in query_lower:
            return self._answer_trial(query, results)
        if "privacy" in query_lower or "data" in query_lower or "gdpr" in query_lower:
            return self._answer_privacy(query, results)
        if "contact" in query_lower or "support" in query_lower or "phone" in query_lower:
            return self._answer_contact(query, results)
        if "price" in query_lower or "cost" in query_lower or "pricing" in query_lower or "$" in query:
            return self._answer_pricing(query, results)
        if "license" in query_lower:
            return self._answer_licensing(query, results)
        if "sla" in query_lower or "uptime" in query_lower:
            return self._answer_sla(query, results)
        if "nonprofit" in query_lower or "non-profit" in query_lower or "discount" in query_lower:
            return self._answer_nonprofit(query, results)

        return self._answer_general(query, results)

    def _find_relevant(self, results: list[dict], keywords: list[str]) -> list[dict]:
        return [
            r for r in results
            if any(kw in r["content"].lower() for kw in keywords)
        ]

    def _answer_refund(self, query: str, results: list[dict]) -> str:
        relevant = self._find_relevant(results, ["refund", "return", "section 1"])
        if not relevant:
            relevant = results[:2]

        return (
            "Based on GigaCorp's Return and Refund Policy (Section 1):\n\n"
            "• **Standard Refund Window:** 30 days from purchase for software products and subscriptions. "
            "After 30 days, refunds are prorated.\n"
            "• **Hardware Returns:** 15 days from delivery in original packaging. A 15% restocking fee applies to opened items.\n"
            "• **Enterprise Contracts:** 60-day cancellation window for full refund on annual contracts.\n"
            "• **Processing Time:** Refunds are processed within 5-10 business days after inspection.\n\n"
            "To request a refund, visit portal.gigacorp.com/refunds or contact Customer Support with your order number."
        )

    def _answer_shipping(self, query: str, results: list[dict]) -> str:
        return (
            "According to GigaCorp's Shipping and Delivery Policy (Section 2):\n\n"
            "• **Standard (5-8 business days):** Free for orders over $500, otherwise $12.99\n"
            "• **Express (2-3 business days):** $24.99\n"
            "• **Next-Day (1 business day):** $39.99\n\n"
            "International shipping takes 7-14 business days via DHL or FedEx. "
            "Customs duties and import taxes are the customer's responsibility.\n\n"
            "Digital products are delivered via email within 1 hour of purchase. "
            "Tracking information is sent via email once physical orders ship."
        )

    def _answer_warranty(self, query: str, results: list[dict]) -> str:
        return (
            "Per GigaCorp's Warranty Policy (Section 3):\n\n"
            "• **Software:** 90-day warranty for substantial conformance to specifications\n"
            "• **GigaBox Appliances:** 2-year limited hardware warranty\n"
            "• **GigaCorp Servers:** 3-year limited hardware warranty\n"
            "• **Peripherals:** 1-year limited warranty\n\n"
            "Warranties exclude damage from misuse, unauthorized modifications, normal wear and tear, "
            "and force majeure events. To file a claim, contact Support with proof of purchase."
        )

    def _answer_password(self, query: str, results: list[dict]) -> str:
        return (
            "To reset your GigaCorp password:\n\n"
            "1. Visit portal.gigacorp.com and click 'Forgot Password'\n"
            "2. Enter your registered email address\n"
            "3. Check your inbox for a password reset link (expires within 1 hour)\n\n"
            "If you don't receive the email, check your spam folder or contact "
            "Customer Support for assistance."
        )

    def _answer_upgrade(self, query: str, results: list[dict]) -> str:
        return (
            "Regarding account upgrades and downgrades (Section 4.6):\n\n"
            "• **Upgrades** take effect immediately upon confirmation\n"
            "• **Downgrades** take effect at the start of the next billing cycle\n"
            "• Partial month credits for downgrades are applied as account credit\n\n"
            "To change your plan, log in to the Customer Portal, go to "
            "'Account Settings' → 'Subscription,' and select your desired plan."
        )

    def _answer_cancellation(self, query: str, results: list[dict]) -> str:
        return (
            "To close your GigaCorp account (Section 4.7):\n\n"
            "• Contact Customer Support to request account closure\n"
            "• Any outstanding balance must be paid before closure\n"
            "• Data will be retained for 90 days after closure, then permanently deleted\n"
            "• Export any data you wish to keep before account closure\n\n"
            "Please note that Enterprise contracts may have early termination fees "
            "as specified in the Master Service Agreement."
        )

    def _answer_billing(self, query: str, results: list[dict]) -> str:
        return (
            "GigaCorp Billing Information (Section 4):\n\n"
            "• **Payment Methods:** Visa, Mastercard, American Express, PayPal, and wire transfers (enterprise)\n"
            "• **Billing Cycles:** Monthly (same day each month) or Annual (20% discount, billed upfront)\n"
            "• **Invoices:** Available in the Customer Portal under 'Billing History' — PDFs for the last 24 months\n"
            "• **Late Payments:** 1.5% monthly late fee after 15 days; service suspended after 30 days; terminated after 60 days\n\n"
            "You can switch billing cycles in the Customer Portal under 'Billing Settings.'"
        )

    def _answer_trial(self, query: str, results: list[dict]) -> str:
        return (
            "GigaCorp offers the following free trials:\n\n"
            "• **GigaAnalytics:** 14-day free trial\n"
            "• **Cloud Services:** 30-day free trial with up to $200 usage credit\n\n"
            "To start a free trial, visit gigacorp.com and sign up for the product you're interested in. "
            "No credit card is required for the GigaAnalytics trial. Cloud services trial requires a "
            "payment method for verification but you won't be charged until the trial ends."
        )

    def _answer_privacy(self, query: str, results: list[dict]) -> str:
        return (
            "GigaCorp's Privacy Policy (Section 7) key points:\n\n"
            "• **Data Collection:** Account data, billing info, usage data, and support communications\n"
            "• **Data Usage:** Account provisioning, transactions, support, product improvement, compliance\n"
            "• **Data Sharing:** We do NOT sell personal data. Shared only with payment processors, "
            "cloud providers, and legal authorities when required.\n"
            "• **Security:** AES-256 encryption at rest, TLS 1.3 in transit, SOC 2 Type II certified\n"
            "• **GDPR:** Full compliance. Contact dpo@gigacorp.com for data protection matters.\n\n"
            "Users can access, correct, delete, and export their data through the Customer Portal."
        )

    def _answer_contact(self, query: str, results: list[dict]) -> str:
        return (
            "You can reach GigaCorp Customer Support through these channels:\n\n"
            "• **Customer Portal:** support.gigacorp.com\n"
            "• **Email:**\n"
            "  - Basic: support@gigacorp.com\n"
            "  - Priority: priority@gigacorp.com\n"
            "  - Premium: premium@gigacorp.com\n"
            "• **Phone:** +1 (555) 123-4567 (Premium customers only, 24/7)\n"
            "• **Chat:** Available in the Customer Portal (Priority and Premium)\n\n"
            "Support is available 24/7 for Premium customers. Basic support response times "
            "are within 24 hours for critical issues."
        )

    def _answer_pricing(self, query: str, results: list[dict]) -> str:
        return (
            "Here are GigaCorp's product pricing highlights (Section 9):\n\n"
            "**Cloud Services:**\n"
            "• GigaCompute: From $0.05/hour\n"
            "• GigaStorage: $0.023/GB/month\n"
            "• GigaDB: From $50/month\n"
            "• GigaCDN: $0.01/GB\n\n"
            "**AI Platform:**\n"
            "• GigaAnalytics: From $299/month\n"
            "• GigaVision: $0.001/image\n"
            "• GigaNLP: $0.0001/request\n"
            "• GigaPredict: From $99/month\n\n"
            "**Enterprise Software (per user/year):**\n"
            "• GigaFlow: $1,000\n"
            "• GigaConnect: $500\n"
            "• GigaSecure: $150\n\n"
            "**Hardware:**\n"
            "• GigaBox Pro: $4,999\n"
            "• GigaBox Enterprise: $12,999\n"
            "• Server R420: From $8,499\n"
            "• Server R820: From $21,999\n\n"
            "Visit gigacorp.com for detailed pricing and custom quotes."
        )

    def _answer_licensing(self, query: str, results: list[dict]) -> str:
        return (
            "GigaCorp Licensing Information (Section 5):\n\n"
            "• **Perpetual License:** One-time fee, includes 1 year of maintenance and updates\n"
            "• **Subscription License:** Monthly/annual recurring fee, includes all updates and support\n"
            "• **Concurrent License:** Based on simultaneous users, requires license server\n\n"
            "Licenses activate via the GigaCorp License Manager or Customer Portal. "
            "Individual licenses can be activated on up to 3 devices.\n"
            "Perpetual licenses are transferable (with $250 fee and written approval); "
            "subscriptions auto-renew unless canceled 7+ days before renewal."
        )

    def _answer_sla(self, query: str, results: list[dict]) -> str:
        return (
            "GigaCorp Service Level Agreement (Section 8.2-8.3):\n\n"
            "• **Core Platform:** 99.9% uptime guarantee\n"
            "• **API Services:** 99.5% uptime guarantee\n"
            "• **Credits:** 5% of monthly fee per full hour of downtime exceeding SLA\n"
            "• **Maximum Credit:** 100% of the monthly fee\n\n"
            "Exclusions: Scheduled maintenance (48-hour notice), force majeure, "
            "customer-caused outages, beta features, and third-party interruptions."
        )

    def _answer_nonprofit(self, query: str, results: list[dict]) -> str:
        return (
            "GigaCorp offers a **25% discount** for verified non-profit organizations.\n\n"
            "To apply:\n"
            "1. Contact our sales team at sales@gigacorp.com\n"
            "2. Submit your non-profit verification documents\n"
            "3. Once approved, the discount will be applied to your account\n\n"
            "Please note that the non-profit discount applies to standard published pricing "
            "and may not be combined with other promotional offers."
        )

    def _answer_general(self, query: str, results: list[dict]) -> str:
        top = results[0]["content"]
        return (
            f"Based on the information I found in GigaCorp's knowledge base:\n\n{top}\n\n"
            f"Is there anything specific about this topic you'd like to know more about? "
            f"I can help with questions about refunds, shipping, warranties, billing, "
            f"technical support, and other GigaCorp services."
        )

    def list_sessions(self) -> list[str]:
        return self.memory.list_sessions()

    def get_history(self, session_id: str) -> list[dict]:
        return self.memory.get_messages(session_id)
