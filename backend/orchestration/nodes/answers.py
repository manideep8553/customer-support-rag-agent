from backend.orchestration.state import ConversationState


def _find_relevant(docs: list[dict], keywords: list[str]) -> list[dict]:
    return [d for d in docs if any(kw in d["content"].lower() for kw in keywords)]


def answer_refund(state: ConversationState) -> dict:
    return {"answer": (
        "Based on GigaCorp's Return and Refund Policy (Section 1):\n\n"
        "• **Standard Refund Window:** 30 days from purchase for software products and subscriptions. "
        "After 30 days, refunds are prorated.\n"
        "• **Hardware Returns:** 15 days from delivery in original packaging. A 15% restocking fee applies to opened items.\n"
        "• **Enterprise Contracts:** 60-day cancellation window for full refund on annual contracts.\n"
        "• **Processing Time:** Refunds are processed within 5-10 business days after inspection.\n\n"
        "To request a refund, visit portal.gigacorp.com/refunds or contact Customer Support with your order number."
    )}


def answer_shipping(state: ConversationState) -> dict:
    return {"answer": (
        "According to GigaCorp's Shipping and Delivery Policy (Section 2):\n\n"
        "• **Standard (5-8 business days):** Free for orders over $500, otherwise $12.99\n"
        "• **Express (2-3 business days):** $24.99\n"
        "• **Next-Day (1 business day):** $39.99\n\n"
        "International shipping takes 7-14 business days via DHL or FedEx. "
        "Customs duties and import taxes are the customer's responsibility.\n\n"
        "Digital products are delivered via email within 1 hour of purchase. "
        "Tracking information is sent via email once physical orders ship."
    )}


def answer_warranty(state: ConversationState) -> dict:
    return {"answer": (
        "Per GigaCorp's Warranty Policy (Section 3):\n\n"
        "• **Software:** 90-day warranty for substantial conformance to specifications\n"
        "• **GigaBox Appliances:** 2-year limited hardware warranty\n"
        "• **GigaCorp Servers:** 3-year limited hardware warranty\n"
        "• **Peripherals:** 1-year limited warranty\n\n"
        "Warranties exclude damage from misuse, unauthorized modifications, normal wear and tear, "
        "and force majeure events. To file a claim, contact Support with proof of purchase."
    )}


def answer_password(state: ConversationState) -> dict:
    return {"answer": (
        "To reset your GigaCorp password:\n\n"
        "1. Visit portal.gigacorp.com and click 'Forgot Password'\n"
        "2. Enter your registered email address\n"
        "3. Check your inbox for a password reset link (expires within 1 hour)\n\n"
        "If you don't receive the email, check your spam folder or contact "
        "Customer Support for assistance."
    )}


def answer_upgrade(state: ConversationState) -> dict:
    return {"answer": (
        "Regarding account upgrades and downgrades (Section 4.6):\n\n"
        "• **Upgrades** take effect immediately upon confirmation\n"
        "• **Downgrades** take effect at the start of the next billing cycle\n"
        "• Partial month credits for downgrades are applied as account credit\n\n"
        "To change your plan, log in to the Customer Portal, go to "
        "'Account Settings' → 'Subscription,' and select your desired plan."
    )}


def answer_cancellation(state: ConversationState) -> dict:
    return {"answer": (
        "To close your GigaCorp account (Section 4.7):\n\n"
        "• Contact Customer Support to request account closure\n"
        "• Any outstanding balance must be paid before closure\n"
        "• Data will be retained for 90 days after closure, then permanently deleted\n"
        "• Export any data you wish to keep before account closure\n\n"
        "Please note that Enterprise contracts may have early termination fees "
        "as specified in the Master Service Agreement."
    )}


def answer_billing(state: ConversationState) -> dict:
    return {"answer": (
        "GigaCorp Billing Information (Section 4):\n\n"
        "• **Payment Methods:** Visa, Mastercard, American Express, PayPal, and wire transfers (enterprise)\n"
        "• **Billing Cycles:** Monthly (same day each month) or Annual (20% discount, billed upfront)\n"
        "• **Invoices:** Available in the Customer Portal under 'Billing History' — PDFs for the last 24 months\n"
        "• **Late Payments:** 1.5% monthly late fee after 15 days; service suspended after 30 days; terminated after 60 days\n\n"
        "You can switch billing cycles in the Customer Portal under 'Billing Settings.'"
    )}


def answer_trial(state: ConversationState) -> dict:
    return {"answer": (
        "GigaCorp offers the following free trials:\n\n"
        "• **GigaAnalytics:** 14-day free trial\n"
        "• **Cloud Services:** 30-day free trial with up to $200 usage credit\n\n"
        "To start a free trial, visit gigacorp.com and sign up for the product you're interested in. "
        "No credit card is required for the GigaAnalytics trial. Cloud services trial requires a "
        "payment method for verification but you won't be charged until the trial ends."
    )}


def answer_privacy(state: ConversationState) -> dict:
    return {"answer": (
        "GigaCorp's Privacy Policy (Section 7) key points:\n\n"
        "• **Data Collection:** Account data, billing info, usage data, and support communications\n"
        "• **Data Usage:** Account provisioning, transactions, support, product improvement, compliance\n"
        "• **Data Sharing:** We do NOT sell personal data. Shared only with payment processors, "
        "cloud providers, and legal authorities when required.\n"
        "• **Security:** AES-256 encryption at rest, TLS 1.3 in transit, SOC 2 Type II certified\n"
        "• **GDPR:** Full compliance. Contact dpo@gigacorp.com for data protection matters.\n\n"
        "Users can access, correct, delete, and export their data through the Customer Portal."
    )}


def answer_contact(state: ConversationState) -> dict:
    return {"answer": (
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
    )}


def answer_pricing(state: ConversationState) -> dict:
    return {"answer": (
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
    )}


def answer_licensing(state: ConversationState) -> dict:
    return {"answer": (
        "GigaCorp Licensing Information (Section 5):\n\n"
        "• **Perpetual License:** One-time fee, includes 1 year of maintenance and updates\n"
        "• **Subscription License:** Monthly/annual recurring fee, includes all updates and support\n"
        "• **Concurrent License:** Based on simultaneous users, requires license server\n\n"
        "Licenses activate via the GigaCorp License Manager or Customer Portal. "
        "Individual licenses can be activated on up to 3 devices.\n"
        "Perpetual licenses are transferable (with $250 fee and written approval); "
        "subscriptions auto-renew unless canceled 7+ days before renewal."
    )}


def answer_sla(state: ConversationState) -> dict:
    return {"answer": (
        "GigaCorp Service Level Agreement (Section 8.2-8.3):\n\n"
        "• **Core Platform:** 99.9% uptime guarantee\n"
        "• **API Services:** 99.5% uptime guarantee\n"
        "• **Credits:** 5% of monthly fee per full hour of downtime exceeding SLA\n"
        "• **Maximum Credit:** 100% of the monthly fee\n\n"
        "Exclusions: Scheduled maintenance (48-hour notice), force majeure, "
        "customer-caused outages, beta features, and third-party interruptions."
    )}


def answer_nonprofit(state: ConversationState) -> dict:
    return {"answer": (
        "GigaCorp offers a **25% discount** for verified non-profit organizations.\n\n"
        "To apply:\n"
        "1. Contact our sales team at sales@gigacorp.com\n"
        "2. Submit your non-profit verification documents\n"
        "3. Once approved, the discount will be applied to your account\n\n"
        "Please note that the non-profit discount applies to standard published pricing "
        "and may not be combined with other promotional offers."
    )}


def answer_general(state: ConversationState) -> dict:
    docs = state.get("retrieved_docs", [])
    if docs:
        top = docs[0].get("content", "GigaCorp policy information.")
    else:
        top = "I don't have enough information to answer that question. Please contact our support team at support@gigacorp.com for further assistance."
    return {"answer": (
        f"{top}\n\n"
        f"Is there anything specific about this topic you'd like to know more about? "
        f"I can help with questions about refunds, shipping, warranties, billing, "
        f"technical support, and other GigaCorp services."
    )}
