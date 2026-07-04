import json, os, re, ssl
from datetime import datetime

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# SSL context that skips verification (fixes certificate issues on some servers)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode    = ssl.CERT_NONE

def _call_claude(prompt, max_tokens=800):
    """Call Claude API. Returns (text, error)."""
    try:
        import urllib.request
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None, "ANTHROPIC_API_KEY not set. Add it as an environment variable."
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        body = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        req  = urllib.request.Request(ANTHROPIC_API_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"], None
    except Exception as e:
        return None, str(e)

def generate_property_description(prop):
    """Generate a professional property listing description using AI."""
    details = f"""
Property Type: {prop.get('property_type','Apartment')}
Category: {prop.get('category','For Sale')}
Title: {prop.get('title','')}
Location: {prop.get('city','')}, {prop.get('state','')}, {prop.get('region','UAE')}
Bedrooms: {prop.get('bedrooms','')}
Bathrooms: {prop.get('bathrooms','')}
Area: {prop.get('area_sqft','')} sqft
Floor: {prop.get('floor','')}
Sale Price: {prop.get('sale_price_aed') or prop.get('sale_price_inr','')}
Monthly Rent: {prop.get('monthly_rent_aed') or prop.get('monthly_rent_inr','')}
Amenities: {', '.join(prop.get('amenities',[]))}
Existing description: {prop.get('description','')}
"""
    prompt = f"""You are a professional real estate copywriter. Write a compelling, professional property listing description for this property. 

{details}

Requirements:
- 3-4 paragraphs, about 150-200 words total
- Professional, engaging tone
- Highlight key features and location benefits
- End with a call to action
- Do NOT include price or contact info
- Write for {prop.get('region','UAE')} market

Return ONLY the description text, no headings or labels."""

    return _call_claude(prompt, max_tokens=500)

def score_lead(lead):
    """Score a lead 1-10 using AI based on available data."""
    prompt = f"""You are a real estate sales expert. Score this lead from 1-10 based on conversion probability.

Lead data:
- Source: {lead.get('source','Unknown')}
- Intent: {lead.get('intent','Unknown')}
- Budget: {lead.get('budget','')} {lead.get('currency','AED')}
- Property interest: {lead.get('prop_type','')}
- Location: {lead.get('location','')}
- Status: {lead.get('status','New')}
- Notes: {lead.get('notes','')}
- Days since created: {(datetime.now() - datetime.strptime(lead.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), '%Y-%m-%d %H:%M:%S')).days if lead.get('created_at') else 0}

Scoring criteria:
- High budget + clear intent = higher score
- Referral/walk-in source = higher than social media
- Specific property type/location = higher
- Already contacted/qualified = higher
- No budget/vague intent = lower

Respond with ONLY a JSON object like: {{"score": 7, "reason": "Clear intent, good budget, referral source", "hot": true}}"""

    text, err = _call_claude(prompt, max_tokens=150)
    if err or not text: return {"score": 5, "reason": "Unable to score", "hot": False}
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()) if m else {"score": 5, "reason": text[:100], "hot": False}
    except:
        return {"score": 5, "reason": "Parse error", "hot": False}

def estimate_property_price(property_type, bedrooms, area_sqft, city, region, category, historical_props):
    """Estimate property price based on historical data."""
    # Build comparable properties data
    comparables = []
    for p in historical_props:
        price = p.get('sale_price_aed') or p.get('sale_price_inr') or p.get('monthly_rent_aed') or p.get('monthly_rent_inr')
        if not price: continue
        if p.get('region') == region and p.get('property_type') == property_type:
            comparables.append({
                'bedrooms': p.get('bedrooms'),
                'area': p.get('area_sqft'),
                'city': p.get('city'),
                'price': price,
                'category': p.get('category')
            })

    prompt = f"""You are a real estate market analyst for {region}.

Target property:
- Type: {property_type}
- Bedrooms: {bedrooms}
- Area: {area_sqft} sqft
- City: {city}
- Category: {category}

Similar properties in database (up to 10):
{json.dumps(comparables[:10], indent=2)}

Based on these comparables and your knowledge of the {region} real estate market, provide a price estimate.

Respond ONLY with JSON: {{"min_price": 500000, "max_price": 650000, "suggested_price": 575000, "currency": "AED", "per_sqft": 1200, "reasoning": "Based on 3 similar units in the area averaging..."}}"""

    text, err = _call_claude(prompt, max_tokens=300)
    if err or not text: return None, err
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()), None
    except:
        return None, "Parse error"

def generate_email_sequence(lead_name, intent, budget, currency, prop_type, location, company_name):
    """Generate 3-email automated sequence for a lead."""
    prompt = f"""You are a real estate marketing expert. Create a 3-email automated sequence for this lead.

Lead: {lead_name}
Intent: {intent}
Budget: {budget} {currency}
Looking for: {prop_type} in {location}
Company: {company_name}

Create 3 emails:
1. Welcome email (sent immediately)
2. Follow-up with property suggestions (sent 3 days later)
3. Urgency/value email (sent 7 days later)

Respond ONLY with JSON:
{{
  "email1": {{"subject": "...", "body": "...", "delay_days": 0}},
  "email2": {{"subject": "...", "body": "...", "delay_days": 3}},
  "email3": {{"subject": "...", "body": "...", "delay_days": 7}}
}}"""

    text, err = _call_claude(prompt, max_tokens=1200)
    if err or not text: return None, err
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()), None
    except:
        return None, "Parse error"
