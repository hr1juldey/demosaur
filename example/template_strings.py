"""
Mock WhatsApp Business API Template Strings for Yawlit Car Wash.
These are pre-approved templates with links that should be sent directly.
"""

# Greeting Template - Initial Engagement
TEMPLATE_GREETING = {
    "name": "greeting_welcome",
    "content": """🚗 Welcome to Yawlit Car Wash!

We provide premium car care services:
✨ Interior & Exterior Wash
💎 Professional Polishing
🔧 Expert Detailing

Type "Hii" to get started or ask us anything!"""
}

# Catalog Template - Service Overview with Links
TEMPLATE_CATALOG = {
    "name": "service_catalog",
    "content": """📋 *Our Services:*

🚗 *WASH* - Interior & Exterior
   Professional deep clean - Basic to Premium tiers available

💎 *POLISHING* - Shine & Protection
   Restore your car's lustre

🔧 *DETAILING* - Complete Care
   Comprehensive interior & exterior treatment

*Tap below to view plans:*
[View Wash Plans](https://yawlit.com/plans/wash)
[View Polish Plans](https://yawlit.com/plans/polish)
[View Detail Plans](https://yawlit.com/plans/detail)"""
}

# Service Plans Template - Tier Selection
TEMPLATE_SERVICE_PLANS = {
    "name": "service_plans_{service_type}",
    "content": """*{service_name} Plans:*

🥉 *Basic* - ₹{basic_price}
   Perfect for regular maintenance

🥈 *Standard* - ₹{standard_price}
   Most popular option

🥇 *Premium* - ₹{premium_price}
   Complete luxury treatment

[Book {service_name}](https://yawlit.com/book/{service_type})"""
}

# Vehicle Types Template
TEMPLATE_VEHICLE_TYPES = {
    "name": "vehicle_types",
    "content": """*Select Your Vehicle Type:*

🚗 Hatchback
🚙 Sedan
🚕 SUV
⚡ Electric Vehicle
👑 Luxury Car

Reply with your vehicle type or type "?help" for guidance"""
}

# Pricing Template - Direct Links
TEMPLATE_PRICING = {
    "name": "pricing_guide",
    "content": """💰 *Complete Pricing Guide*

[View All Prices](https://yawlit.com/pricing)
[Service Comparison](https://yawlit.com/compare)

*Quick Pricing:*
• Basic Wash: ₹299-599
• Standard Polish: ₹799-1299
• Premium Detail: ₹1999-3499

Vehicle type affects pricing. Select your vehicle for accurate quote."""
}

# Booking Confirmation Template
TEMPLATE_BOOKING_CONFIRMATION = {
    "name": "booking_confirmation",
    "content": """✅ *Booking Confirmed!*

📝 Service: {service_name}
🚗 Vehicle: {vehicle_brand} {vehicle_model}
📅 Date: {booking_date}
⏰ Time: {booking_time}
💰 Amount: ₹{amount}

[Download Ticket](https://yawlit.com/ticket/{ticket_id})
[Track Service](https://yawlit.com/track/{booking_id})

Ticket #{ticket_id} sent to your email.
Thank you for choosing Yawlit! 🙏"""
}

# Reschedule Template - Alternative Dates
TEMPLATE_ALTERNATIVE_DATES = {
    "name": "alternative_dates",
    "content": """📅 *Selected Date Unavailable*

Available slots nearby:

{date_options}

Reply with your preferred date or type "?show more" for additional options

[Check Full Calendar](https://yawlit.com/calendar)"""
}

# Templates Registry - Easy lookup
TEMPLATES = {
    "greeting": TEMPLATE_GREETING,
    "catalog": TEMPLATE_CATALOG,
    "plans": TEMPLATE_SERVICE_PLANS,
    "vehicles": TEMPLATE_VEHICLE_TYPES,
    "pricing": TEMPLATE_PRICING,
    "confirmation": TEMPLATE_BOOKING_CONFIRMATION,
    "alternatives": TEMPLATE_ALTERNATIVE_DATES,
}


def get_template(template_key: str) -> dict:
    """Retrieve template by key."""
    return TEMPLATES.get(template_key, {})


def render_template(template_key: str, **kwargs) -> str:
    """Render template with variables."""
    template = TEMPLATES.get(template_key, {})
    if not template:
        return ""

    content = template.get("content", "")
    for key, value in kwargs.items():
        content = content.replace(f"{{{key}}}", str(value))

    return content