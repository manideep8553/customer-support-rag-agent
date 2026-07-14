import re
from typing import Optional

from backend.orchestration.state import ConversationState


def _cd(state: ConversationState) -> dict:
    return state.get("customer_data", {}) or {}


def _find_relevant(docs: list[dict], keywords: list[str]) -> list[dict]:
    return [d for d in docs if any(kw in d["content"].lower() for kw in keywords)]


def answer_shipping(state: ConversationState) -> dict:
    customer = _cd(state)
    addr = customer.get("default_address")
    addr_block = ""
    if addr:
        line2 = f", {addr['street_line2']}" if addr.get("street_line2") else ""
        addr_block = (
            f"\n\n**Your default shipping address:**\n"
            f"{addr['street_line1']}{line2}\n"
            f"{addr['city']}, {addr['state']} {addr['postal_code']}\n"
            f"{addr['country']}\n"
        )
    orders = customer.get("recent_orders", [])
    shipped = [o for o in orders if o.get("status") in ("shipped", "confirmed", "processing")]
    shipping_block = ""
    if shipped:
        shipping_block = "\n\n**Your recent shipments:**\n"
        for o in shipped[:2]:
            tracking = f" (Tracking: {o.get('tracking_number', 'N/A')} via {o.get('carrier', 'N/A')})" if o.get("tracking_number") else ""
            eta = f" — Est. delivery: {o.get('estimated_delivery', 'N/A')}" if o.get("estimated_delivery") else ""
            shipping_block += f"• Order {o['order_number']}: {o['status'].title()}{tracking}{eta}\n"

    if customer.get("default_address") and customer["default_address"].get("country", "").lower() != "united states":
        addr_country = customer["default_address"]["country"]
        return {"answer": (
            f"**International Shipping to {addr_country}**\n\n"
            f"Based on GigaCorp's Shipping and Delivery Policy, international orders to {addr_country} "
            f"typically take 7-14 business days via DHL or FedEx. Customs duties and import taxes "
            f"are the customer's responsibility.{addr_block}{shipping_block}\n\n"
            f"Standard shipping (5-8 business days) is free for orders over $500, otherwise $12.99. "
            f"Express (2-3 days) is $24.99, and Next-Day is $39.99.\n\n"
            f"Digital products are delivered via email within 1 hour of purchase."
        )}

    return {"answer": (
        "According to GigaCorp's Shipping and Delivery Policy:\n\n"
        "• **Standard (5-8 business days):** Free for orders over $500, otherwise $12.99\n"
        "• **Express (2-3 business days):** $24.99\n"
        "• **Next-Day (1 business day):** $39.99\n\n"
        "International shipping takes 7-14 business days via DHL or FedEx. "
        "Customs duties and import taxes are the customer's responsibility.\n\n"
        "Digital products are delivered via email within 1 hour of purchase. "
        "Tracking information is sent via email once physical orders ship."
        f"{addr_block}{shipping_block}"
    )}


def answer_refund(state: ConversationState) -> dict:
    customer = _cd(state)
    orders = customer.get("recent_orders", [])
    refundable = [o for o in orders if o.get("status") in ("delivered", "shipped")]
    order_block = ""
    if refundable:
        order_block = "\n\n**Orders eligible for refund/return:**\n"
        for o in refundable[:2]:
            days_ago = ""
            order_block += f"• {o['order_number']} — {', '.join(i['product_name'] for i in o.get('items', []))}{days_ago}\n"

    return {"answer": (
        "Based on GigaCorp's Return and Refund Policy:\n\n"
        "• **Standard Refund Window:** 30 days from purchase for software products and subscriptions. "
        "After 30 days, refunds are prorated.\n"
        "• **Hardware Returns:** 15 days from delivery in original packaging. A 15% restocking fee applies to opened items.\n"
        "• **Enterprise Contracts:** 60-day cancellation window for full refund on annual contracts.\n"
        "• **Processing Time:** Refunds are processed within 5-10 business days after inspection.\n\n"
        "To request a refund, visit portal.gigacorp.com/refunds or contact Customer Support with your order number."
        f"{order_block}"
    )}


def answer_warranty(state: ConversationState) -> dict:
    customer = _cd(state)
    warranty_items = []
    for o in customer.get("recent_orders", []):
        for i in o.get("items", []):
            if i.get("warranty_months") or i.get("warranty_expires"):
                warranty_items.append(i)
    item_block = ""
    if warranty_items:
        item_block = "\n\n**Your items under warranty:**\n"
        for i in warranty_items:
            expires = f" (expires {i['warranty_expires']})" if i.get("warranty_expires") else f" ({i['warranty_months']}-month warranty)"
            item_block += f"• {i['product_name']}{expires}\n"

    return {"answer": (
        "Per GigaCorp's Warranty Policy:\n\n"
        "• **Software:** 90-day warranty for substantial conformance to specifications\n"
        "• **GigaBox Appliances:** 2-year limited hardware warranty\n"
        "• **GigaCorp Servers:** 3-year limited hardware warranty\n"
        "• **Peripherals:** 1-year limited warranty\n\n"
        "Warranties exclude damage from misuse, unauthorized modifications, normal wear and tear, "
        "and force majeure events. To file a claim, contact Support with proof of purchase."
        f"{item_block}"
    )}


def answer_billing(state: ConversationState) -> dict:
    customer = _cd(state)
    methods = customer.get("payment_methods", [])
    subs = customer.get("subscriptions", [])
    pm_block = ""
    if methods:
        pm_block = "\n\n**Your saved payment methods:**\n"
        for m in methods:
            label = m.get("label", m["method_type"].replace("_", " ").title())
            default = " (Default)" if m.get("is_default") else ""
            pm_block += f"• {label}{default}\n"
    sub_block = ""
    if subs:
        sub_block = "\n\n**Your active subscriptions:**\n"
        for s in subs:
            next_bill = f" — Next billing: {s.get('next_billing_at', 'N/A')}" if s.get("next_billing_at") else ""
            sub_block += f"• {s['plan_name']} (${s['amount']:.2f}/{s['billing_cycle']}){next_bill}\n"

    return {"answer": (
        "GigaCorp Billing Information:\n\n"
        "• **Payment Methods:** Visa, Mastercard, American Express, PayPal, and wire transfers (enterprise)\n"
        "• **Billing Cycles:** Monthly (same day each month) or Annual (20% discount, billed upfront)\n"
        "• **Invoices:** Available in the Customer Portal under 'Billing History' — PDFs for the last 24 months\n"
        "• **Late Payments:** 1.5% monthly late fee after 15 days; service suspended after 30 days; terminated after 60 days\n\n"
        "You can switch billing cycles in the Customer Portal under 'Billing Settings.'"
        f"{pm_block}{sub_block}"
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
    customer = _cd(state)
    sub_block = ""
    subs = customer.get("subscriptions", [])
    if subs:
        sub_block = "\n\n**Your current plans:**\n"
        for s in subs:
            sub_block += f"• {s['plan_name']} — ${s['amount']:.2f}/{s['billing_cycle']} ({s['status']})\n"
    return {"answer": (
        "Regarding account upgrades and downgrades:\n\n"
        "• **Upgrades** take effect immediately upon confirmation\n"
        "• **Downgrades** take effect at the start of the next billing cycle\n"
        "• Partial month credits for downgrades are applied as account credit\n\n"
        "To change your plan, log in to the Customer Portal, go to "
        "'Account Settings' → 'Subscription,' and select your desired plan."
        f"{sub_block}"
    )}


def answer_cancellation(state: ConversationState) -> dict:
    customer = _cd(state)
    sub_block = ""
    subs = customer.get("subscriptions", [])
    if subs:
        sub_block = "\n\n**Your active subscriptions that would be affected:**\n"
        for s in subs:
            if s['status'] == 'active':
                sub_block += f"• {s['plan_name']} (${s['amount']:.2f}/{s['billing_cycle']}) — next billing: {s.get('next_billing_at', 'N/A')}\n"
    return {"answer": (
        "To close your GigaCorp account:\n\n"
        "• Contact Customer Support to request account closure\n"
        "• Any outstanding balance must be paid before closure\n"
        "• Data will be retained for 90 days after closure, then permanently deleted\n"
        "• Export any data you wish to keep before account closure\n\n"
        "Please note that Enterprise contracts may have early termination fees "
        "as specified in the Master Service Agreement."
        f"{sub_block}"
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
        "GigaCorp's Privacy Policy key points:\n\n"
        "• **Data Collection:** Account data, billing info, usage data, and support communications\n"
        "• **Data Usage:** Account provisioning, transactions, support, product improvement, compliance\n"
        "• **Data Sharing:** We do NOT sell personal data. Shared only with payment processors, "
        "cloud providers, and legal authorities when required.\n"
        "• **Security:** AES-256 encryption at rest, TLS 1.3 in transit, SOC 2 Type II certified\n"
        "• **GDPR:** Full compliance. Contact dpo@gigacorp.com for data protection matters.\n\n"
        "Users can access, correct, delete, and export their data through the Customer Portal."
    )}


def answer_contact(state: ConversationState) -> dict:
    customer = _cd(state)
    tier_info = ""
    loyalty = customer.get("loyalty", {})
    tier = loyalty.get("tier", "")
    if tier:
        tier_info = f"\n\nAs a **{tier.title()}** loyalty member, you have access to:\n"
        if tier == "platinum":
            tier_info += "• 24/7 premium phone and chat support\n• Dedicated account manager\n• Priority email response (< 1 hour)"
        elif tier == "gold":
            tier_info += "• Priority phone support during business hours\n• Dedicated account manager\n• Priority email response (< 4 hours)"
        elif tier == "silver":
            tier_info += "• Priority email support\n• Chat support during business hours"
        else:
            tier_info += "• Standard email and chat support during business hours"
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
        f"{tier_info}"
    )}


def answer_pricing(state: ConversationState) -> dict:
    customer = _cd(state)
    loyalty = customer.get("loyalty", {})
    tier = loyalty.get("tier", "")
    discount = ""
    if tier == "platinum":
        discount = "\n\n**As a Platinum member, you receive a 20% discount on all plans.**"
    elif tier == "gold":
        discount = "\n\n**As a Gold member, you receive a 15% discount on annual plans.**"
    elif tier == "silver":
        discount = "\n\n**As a Silver member, you receive a 10% discount on annual plans.**"
    return {"answer": (
        "Here are GigaCorp's product pricing highlights:\n\n"
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
        f"{discount}"
    )}


def answer_licensing(state: ConversationState) -> dict:
    customer = _cd(state)
    orders = customer.get("recent_orders", [])
    license_items = []
    for o in orders:
        for i in o.get("items", []):
            if i.get("product_category") == "Software":
                license_items.append(i)
    lic_block = ""
    if license_items:
        lic_block = "\n\n**Your licensed products:**\n"
        for i in license_items:
            lic_block += f"• {i['product_name']} (Qty: {i['quantity']})\n"
    return {"answer": (
        "GigaCorp Licensing Information:\n\n"
        "• **Perpetual License:** One-time fee, includes 1 year of maintenance and updates\n"
        "• **Subscription License:** Monthly/annual recurring fee, includes all updates and support\n"
        "• **Concurrent License:** Based on simultaneous users, requires license server\n\n"
        "Licenses activate via the GigaCorp License Manager or Customer Portal. "
        "Individual licenses can be activated on up to 3 devices.\n"
        "Perpetual licenses are transferable (with $250 fee and written approval); "
        "subscriptions auto-renew unless canceled 7+ days before renewal."
        f"{lic_block}"
    )}


def answer_sla(state: ConversationState) -> dict:
    return {"answer": (
        "GigaCorp Service Level Agreement:\n\n"
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


def answer_invoice(state: ConversationState) -> dict:
    customer = _cd(state)
    orders = customer.get("recent_orders", [])
    inv_block = ""
    for o in orders[:3]:
        pmt = "Paid" if o.get("status") in ("delivered", "shipped", "confirmed") else "Pending"
        inv_block += (
            f"• **{o['order_number']}**: ${o['total']:.2f} — {pmt}\n"
            f"  Items: {', '.join(i['product_name'] for i in o.get('items', []))}\n"
        )
    return {"answer": (
        "**Your Invoices & Billing Summary**\n\n"
        f"{inv_block}\n"
        "Invoices are available in the Customer Portal under 'Billing History' as downloadable PDFs. "
        "You can access invoices for the last 24 months.\n\n"
        "To download a specific invoice, visit portal.gigacorp.com/invoices or contact support."
    )}


def answer_return_policy(state: ConversationState) -> dict:
    customer = _cd(state)
    orders = customer.get("recent_orders", [])
    returnable = [o for o in orders if o.get("status") in ("delivered", "shipped")]
    ret_block = ""
    if returnable:
        ret_block = "\n\n**Orders eligible for return:**\n"
        for o in returnable[:2]:
            items_str = ", ".join(i['product_name'] for i in o.get('items', []))
            ret_block += f"• {o['order_number']} — {items_str}\n"
    return {"answer": (
        "**GigaCorp Return Policy**\n\n"
        "• **Return Window:** 30 days from delivery for most products; 15 days for opened hardware\n"
        "• **Condition:** Items must be in original packaging with all accessories\n"
        "• **RMA Required:** A Return Merchandise Authorization (RMA) number is needed before shipping returns\n"
        "• **Restocking Fee:** 15% on opened hardware items\n"
        "• **Processing:** Refunds issued within 5-10 business days after inspection\n\n"
        "To start a return, contact Customer Support or submit a request in the Customer Portal. "
        "You will receive an RMA number and prepaid return label via email."
        f"{ret_block}"
    )}


def answer_exchange(state: ConversationState) -> dict:
    customer = _cd(state)
    orders = customer.get("recent_orders", [])
    exch_block = ""
    for o in orders:
        for i in o.get("items", []):
            if i.get("product_category") == "Hardware":
                exch_block += f"• {o['order_number']} — {i['product_name']}\n"
    hardware_block = ""
    if exch_block:
        hardware_block = f"\n\n**Hardware items in your recent orders eligible for exchange:**\n{exch_block}"
    return {"answer": (
        "**GigaCorp Exchange Policy**\n\n"
        "• **Eligibility:** Hardware items within 30 days of delivery can be exchanged\n"
        "• **Condition:** Items must be in original packaging with all accessories\n"
        "• **Process:** You will receive a prepaid return label. Replacement ships after the returned item is inspected.\n"
        "• **Price Difference:** If the replacement costs more, the difference must be paid. "
        "If it costs less, the difference is refunded.\n"
        "• **Expedited Exchange:** Available for premium customers — replacement ships immediately with a hold on your payment method."
        f"{hardware_block}\n\n"
        "To start an exchange, contact Customer Support with your order number and desired replacement product."
    )}


TRACKING_NUMBER_RE = re.compile(r'\b([A-Z0-9]{6,30})\b')


def _find_tracking_number(query: str, customer: dict) -> Optional[str]:
    numbers = TRACKING_NUMBER_RE.findall(query.upper())
    shipments = customer.get("shipments", [])
    for num in numbers:
        for s in shipments:
            if s.get("tracking_number", "").upper() == num:
                return s["tracking_number"]
            if num in s.get("tracking_number", "").upper():
                return s["tracking_number"]
    return None


def answer_tracking(state: ConversationState) -> dict:
    customer = _cd(state)
    query = state.get("query", "")
    shipments = customer.get("shipments", [])
    discussed = state.get("discussed_entities", {}) or {}
    customer.get("recent_orders", [])
    new_entities = dict(discussed)

    matched_tn = _find_tracking_number(query, customer)
    target = None
    if matched_tn:
        for s in shipments:
            if s["tracking_number"] == matched_tn:
                target = s
                break

    if not target and discussed.get("order"):
        for s in shipments:
            if s.get("order_number") == discussed["order"]:
                target = s
                break

    if not target and shipments:
        target = shipments[0]

    if not target:
        return {"answer": (
            "I don't see any active shipments on your account. "
            "If you have a tracking number, please share it and I can look it up for you."
        ), "discussed_entities": new_entities}

    if target.get("tracking_number"):
        new_entities["tracking"] = target["tracking_number"]
    if target.get("order_number"):
        new_entities["order"] = target["order_number"]

    status_icons = {
        "pre_transit": "📋", "in_transit": "🚚",
        "out_for_delivery": "📬", "delivered": "✅",
        "exception": "⚠️", "returned": "↩️",
        "available_for_pickup": "📮",
    }
    icon = status_icons.get(target["status"], "•")

    base = (
        f"{icon} **Shipment Status:** {target['status_label']}\n"
        f"📦 **Carrier:** {target['courier']}\n"
        f"🔢 **Tracking:** {target['tracking_number']}\n"
    )
    if target.get("current_location"):
        base += f"📍 **Current Location:** {target['current_location']}\n"
    if target.get("estimated_delivery"):
        base += f"📅 **Estimated Delivery:** {target['estimated_delivery']}\n"
    if target.get("last_update"):
        base += f"🕐 **Last Updated:** {target['last_update']}\n"
    if target.get("order_number"):
        base += f"🛒 **Order:** {target['order_number']}\n"

    if target["status"] == "pre_transit":
        detail = "\nYour package has been registered in the shipping system but is not yet with the carrier. It will be picked up soon."
    elif target["status"] == "in_transit":
        detail = "\nYour package is on its way and moving through the carrier network. Check back for the next location update."
    elif target["status"] == "out_for_delivery":
        detail = "\nYour package is out for delivery today! Please ensure someone is available to receive it."
    elif target["status"] == "delivered":
        detail = "\nYour package has been delivered successfully."
    elif target["status"] == "exception":
        detail = "\nThere is a delivery exception. Please contact the carrier or our support team for assistance."
    else:
        detail = ""

    return {"answer": f"{base}{detail}", "discussed_entities": new_entities}


ORDER_NUMBER_RE = re.compile(r'\b(ORD-\d{4}-\d{3})\b', re.I)


def _resolve_order_number(query: str, orders: list[dict], discussed: dict) -> str | None:
    q = query.upper()
    m = ORDER_NUMBER_RE.search(q)
    if m:
        return m.group(1).upper()

    prev_order = discussed.get("order")
    if prev_order:
        for o in orders:
            if o["order_number"] == prev_order:
                return prev_order

    if len(orders) == 1:
        return orders[0]["order_number"]

    return None


def answer_order_status(state: ConversationState) -> dict:
    customer = _cd(state)
    orders = customer.get("recent_orders", [])
    if not orders:
        return {"answer": (
            "I don't see any recent orders on your account. If you believe this is an error, "
            "please contact our support team at support@gigacorp.com for assistance."
        )}

    discussed = state.get("discussed_entities", {}) or {}
    query = state.get("query", "")
    resolved_order = _resolve_order_number(query, orders, discussed)
    new_entities = dict(discussed)

    if resolved_order:
        new_entities["order"] = resolved_order
        matched = [o for o in orders if o["order_number"] == resolved_order]
        if matched:
            o = matched[0]
            status_icon = {
                "pending": "⏳", "confirmed": "✅", "processing": "🔧",
                "shipped": "📦", "delivered": "📬", "cancelled": "❌", "refunded": "💰",
            }.get(o["status"], "•")
            tracking = ""
            if o.get("tracking_number"):
                tracking = f" — Tracking: {o['tracking_number']}"
                if o.get("carrier"):
                    tracking += f" ({o['carrier']})"
            eta = ""
            if o.get("estimated_delivery"):
                eta = f" — Est. delivery: {o['estimated_delivery']}"
            items_str = ", ".join(i["product_name"] for i in o.get("items", []))
            return {"answer": (
                f"{status_icon} **{o['order_number']}** — {o['status'].title()}"
                f"{tracking}{eta}\n"
                f"  Items: {items_str}\n"
                f"  Total: ${o['total']:.2f}\n\n"
                "You can view full order details and history in the Customer Portal."
            ), "discussed_entities": new_entities}
    else:
        new_entities.pop("order", None)

    order_block = ""
    for o in orders:
        status_icon = {
            "pending": "⏳", "confirmed": "✅", "processing": "🔧",
            "shipped": "📦", "delivered": "📬", "cancelled": "❌", "refunded": "💰",
        }.get(o["status"], "•")
        tracking = ""
        if o.get("tracking_number"):
            tracking = f" — Tracking: {o['tracking_number']}"
            if o.get("carrier"):
                tracking += f" ({o['carrier']})"
        eta = ""
        if o.get("estimated_delivery"):
            eta = f" — Est. delivery: {o['estimated_delivery']}"
        items_str = ", ".join(i["product_name"] for i in o.get("items", []))
        order_block += (
            f"{status_icon} **{o['order_number']}** — {o['status'].title()}"
            f"{tracking}{eta}\n"
            f"  Items: {items_str}\n"
            f"  Total: ${o['total']:.2f}\n\n"
        )
    return {"answer": (
        f"Here are your recent orders:\n\n{order_block}"
        "You can view full order details and history in the Customer Portal."
    ), "discussed_entities": new_entities}


def answer_loyalty(state: ConversationState) -> dict:
    customer = _cd(state)
    loyalty = customer.get("loyalty", {})
    if not loyalty:
        return {"answer": (
            "I don't see a loyalty account associated with your profile. "
            "Loyalty accounts are automatically created when you place your first order."
        )}
    tier = loyalty.get("tier", "bronze").title()
    points = loyalty.get("points", 0)
    spent = loyalty.get("total_spent", 0)
    total_orders = loyalty.get("total_orders", 0)
    next_tier = loyalty.get("next_tier")
    points_needed = loyalty.get("points_to_next_tier")
    progress = ""
    if next_tier and points_needed:
        progress = f"\n\nYou need **{points_needed} more points** to reach **{next_tier.title()}** tier."
    tier_benefits_map = {
        "bronze": "Basic support, standard response times",
        "silver": "Priority support, 10% discount on annual plans",
        "gold": "Priority support, 15% discount, dedicated account manager",
        "platinum": "24/7 premium support, 20% discount, dedicated manager, early access to new products",
    }
    benefits = tier_benefits_map.get(loyalty.get("tier", ""), "")
    return {"answer": (
        f"**Your GigaCorp Loyalty Account**\n\n"
        f"• **Tier:** {tier}\n"
        f"• **Points:** {points:,}\n"
        f"• **Total Orders:** {total_orders}\n"
        f"• **Total Spent:** ${spent:,.2f}\n"
        f"• **Benefits:** {benefits}"
        f"{progress}\n\n"
        "You earn points on every purchase. Points never expire as long as your account remains active."
    )}


STATUS_ICONS = {
    "open": "🆕", "in_progress": "🔧", "waiting_customer": "📞",
    "escalated": "🚨", "resolved": "✅", "closed": "🔒",
}
PRIORITY_LABELS = {
    "low": "Low", "medium": "Medium", "high": "High", "critical": "Critical",
}


TICKET_NUMBER_RE = re.compile(r'\b(TKT-\d{4}-\d{4})\b', re.I)


def answer_ticket(state: ConversationState) -> dict:
    customer = _cd(state)
    query = state.get("query", "")
    open_tickets = customer.get("open_tickets", [])
    all_tickets = customer.get("all_tickets", open_tickets)
    discussed = state.get("discussed_entities", {}) or {}
    new_entities = dict(discussed)

    if not all_tickets:
        return {"answer": (
            "You don't have any support tickets on your account. "
            "If you need help, you can create a new ticket through the Customer Portal "
            "or contact our support team at support@gigacorp.com."
        ), "discussed_entities": new_entities}

    matched_tn = None
    q = query.upper()
    m = TICKET_NUMBER_RE.search(q)
    if m:
        matched_tn = m.group(1).upper()

    prev_ticket = discussed.get("ticket") if not matched_tn else None
    single_ticket = None
    if matched_tn:
        for t in all_tickets:
            if t["ticket_number"] == matched_tn:
                single_ticket = t
                break
    elif prev_ticket:
        for t in all_tickets:
            if t["ticket_number"] == prev_ticket:
                single_ticket = t
                break

    if single_ticket:
        new_entities["ticket"] = single_ticket["ticket_number"]
        icon = STATUS_ICONS.get(single_ticket.get("status", ""), "•")
        pri = PRIORITY_LABELS.get(single_ticket.get("priority", ""), single_ticket.get("priority", ""))
        return {"answer": (
            f"{icon} **{single_ticket['ticket_number']}** — {single_ticket['subject'][:100]}\n"
            f"   Status: {single_ticket.get('status_label', single_ticket['status'].replace('_', ' ').title())} "
            f"| Priority: {pri}\n"
            f"   Category: {single_ticket.get('category', 'N/A')}\n"
            f"   Opened: {single_ticket.get('opened_at', 'N/A')}\n"
            + (f"   Assigned to: {single_ticket['assigned_to']}\n" if single_ticket.get("assigned_to") else "")
            + "You can view full details in the Customer Portal."
        ), "discussed_entities": new_entities}

    new_entities.pop("ticket", None)
    ticket_block = ""
    for t in all_tickets[:5]:
        icon = STATUS_ICONS.get(t.get("status", ""), "•")
        pri = PRIORITY_LABELS.get(t.get("priority", ""), t.get("priority", ""))
        ticket_block += (
            f"{icon} **{t['ticket_number']}** — {t['subject'][:60]}\n"
            f"   Status: {t.get('status_label', t['status'].replace('_', ' ').title())} "
            f"| Priority: {pri}\n"
        )
        if t.get("category"):
            ticket_block += f"   Category: {t['category']}\n"
        if t.get("assigned_to"):
            ticket_block += f"   Assigned to: {t['assigned_to']}\n"
        ticket_block += "\n"
    return {"answer": (
        f"**Your Support Tickets** ({len(all_tickets)} total)\n\n"
        f"{ticket_block}"
        "You can view full ticket details, add comments, or create new tickets "
        "in the Customer Portal at support.gigacorp.com."
    ), "discussed_entities": new_entities}


def answer_general(state: ConversationState) -> dict:
    docs = state.get("retrieved_docs", [])
    customer = _cd(state)
    name = customer.get("display_name", "")
    greeting = f"Hi {name}, " if name else ""
    if docs:
        top = docs[0].get("content", "GigaCorp policy information.")
        return {"answer": (
            f"{greeting}{top}\n\n"
            f"Is there anything specific about this topic you'd like to know more about? "
            f"I can help with questions about refunds, shipping, warranties, billing, "
            f"technical support, and other GigaCorp services."
        )}
    return {"answer": (
        f"{greeting}I don't have enough information to answer that question. "
        f"Please contact our support team at support@gigacorp.com for further assistance.\n\n"
        f"Is there anything specific you'd like to know more about? "
        f"I can help with questions about refunds, shipping, warranties, billing, "
        f"technical support, and other GigaCorp services."
    )}
