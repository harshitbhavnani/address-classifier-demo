import os
import math
import json
import requests
from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
import re
from typing import Dict, List, Optional

# ---------- CONFIG ----------

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if OPENAI_API_KEY is None:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# ---------- HTML TEMPLATE ----------

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Address Classifier Demo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(135deg, #0f172a, #1e293b, #0369a1);
      color: #e5e7eb;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .wrapper {
      width: 100%;
      max-width: 700px;
      padding: 24px;
    }
    .card {
      background: rgba(15, 23, 42, 0.95);
      border-radius: 20px;
      padding: 24px 24px 20px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.4);
      border: 1px solid rgba(148, 163, 184, 0.35);
      backdrop-filter: blur(10px);
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 18px;
    }
    .logo {
      width: 60px;
      height: 60px;
      border-radius: 999px;
      background: radial-gradient(circle at 30% 30%, #38bdf8, #0f172a);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      color: #e5e7eb;
      font-size: 18px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
    }
    .subtitle {
      font-size: 13px;
      color: #9ca3af;
      margin-top: 3px;
    }
    label {
      font-size: 13px;
      display: block;
      margin-bottom: 4px;
      color: #e5e7eb;
    }
    textarea {
      width: 100%;
      min-height: 90px;
      border-radius: 12px;
      border: 1px solid #4b5563;
      padding: 10px 12px;
      font-size: 14px;
      resize: vertical;
      outline: none;
      background: #020617;
      color: #e5e7eb;
    }
    textarea:focus {
      border-color: #38bdf8;
      box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.4);
    }
    .actions {
      margin-top: 12px;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      align-items: center;
    }
    button {
      border: none;
      border-radius: 999px;
      padding: 8px 18px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      background: linear-gradient(135deg, #38bdf8, #0ea5e9);
      color: #0f172a;
      box-shadow: 0 10px 25px rgba(56, 189, 248, 0.35);
      transition: transform 0.08s ease, box-shadow 0.08s ease;
    }
    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 14px 30px rgba(56, 189, 248, 0.45);
    }
    button:active {
      transform: translateY(0);
      box-shadow: 0 8px 18px rgba(56, 189, 248, 0.35);
    }
    .result {
      margin-top: 18px;
      padding: 14px 14px 12px;
      border-radius: 14px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(148, 163, 184, 0.5);
    }
    .result-title {
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #9ca3af;
      margin-bottom: 6px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      border: 1px solid rgba(148, 163, 184, 0.7);
      margin-bottom: 6px;
    }
    .pill.residential { background: rgba(34, 197, 94, 0.18); border-color: rgba(34, 197, 94, 0.8); color: #bbf7d0; }
    .pill.business    { background: rgba(56, 189, 248, 0.18); border-color: rgba(56, 189, 248, 0.8); color: #bae6fd; }
    .pill.unknown     { background: rgba(148, 163, 184, 0.18); border-color: rgba(148, 163, 184, 0.8); color: #e5e7eb; }
    .address-text {
      font-size: 13px;
      color: #e5e7eb;
      white-space: pre-wrap;
      margin-bottom: 8px;
    }
    .meta {
      font-size: 12px;
      color: #9ca3af;
      margin-bottom: 6px;
    }
    .reason {
      font-size: 13px;
      color: #d1d5db;
    }
    .footer {
      margin-top: 8px;
      font-size: 11px;
      color: #6b7280;
      text-align: right;
    }
    @media (max-width: 600px) {
      .card {
        padding: 18px 16px 14px;
      }
    }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="card">
      <div class="header">
        <div class="logo">FMB</div>
        <div>
          <h1>Address Classifier</h1>
          <div class="subtitle">Classify an address as residential, business, or unknown using Google Places + LLM.</div>
        </div>
      </div>

      <form method="post">
        <label for="address">Paste an address</label>
        <textarea id="address" name="address" placeholder="e.g. 1801 Century Park E Ste 2050
Los Angeles, CA 90067
United States">{{ request.form.get('address', '') }}</textarea>

        <div class="actions">
          <button type="submit">Classify Address</button>
        </div>
      </form>

      {% if result %}
      <div class="result">
        <div class="result-title">Result</div>
        <div class="pill {{ result.category }}">
          <span>&#9679;</span>
          <span>{{ result.category|upper }}</span>
        </div>

        <div class="address-text">{{ result.address }}</div>
        <div class="meta">
          Confidence: {{ "%.2f"|format(result.confidence) }}<br>
          Nearby places checked: {{ result.get("nearby_count", "N/A") }}
        </div>
        <div class="reason">{{ result.reason }}</div>
      </div>
      {% endif %}

      <div class="footer">
        Demo only &middot; Do not use for production decisions.
      </div>
    </div>
  </div>
</body>
</html>
"""

# ---------- CORE LOGIC (YOUR NOTEBOOK CODE, ADAPTED) ----------

def haversine_distance_m(lat1, lon1, lat2, lon2):
    """Distance in meters between two lat/lng points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def extract_address_features(address: str) -> dict:
    """Extract structural features from address text."""
    addr_lower = address.lower()
    
    # Business indicators
    suite_pattern = r'\b(ste|suite|office|floor|fl|bldg|building)\b\.?\s*\d+|#[a-z]'
    has_suite = bool(re.search(suite_pattern, addr_lower))
    
    # Residential indicators  
    apt_pattern = r'\b(apt|apartment|unit)\b\.?\s*\d+|#\d+'
    has_apartment = bool(re.search(apt_pattern, addr_lower))
    
    return {
        "has_suite_office": has_suite,
        "has_apartment_unit": has_apartment,
    }
    
def get_place_context(address: str, GOOGLE_PLACES_API_KEY: str, radius_m: int = 50) -> dict:
    """
    Focused approach: single search with distance-tiered nearby analysis.
    Also attempts text search to find building names.
    """
    # Single Find Place search
    find_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    find_params = {
        "key": GOOGLE_PLACES_API_KEY,
        "input": address,
        "inputtype": "textquery",
        "fields": "name,formatted_address,types,business_status,user_ratings_total,geometry,place_id,rating",
    }
    
    # Also try Text Search API for better building name detection
    textsearch_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    textsearch_params = {
        "key": GOOGLE_PLACES_API_KEY,
        "query": address,
    }
    
    # Try both APIs
    main_place = None
    lat, lng = None, None
    alternative_names = []
    
    try:
        r = requests.get(find_url, params=find_params, timeout=10)
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates", [])
        
        if candidates:
            c = candidates[0]
            loc = c.get("geometry", {}).get("location", {})
            lat, lng = loc.get("lat"), loc.get("lng")
            
            main_place = {
                "name": c.get("name"),
                "formatted_address": c.get("formatted_address"),
                "types": c.get("types", []),
                "business_status": c.get("business_status"),
                "user_ratings_total": c.get("user_ratings_total", 0),
                "rating": c.get("rating"),
                "lat": lat,
                "lng": lng,
            }
    except Exception as e:
        pass
    
    # Try text search to find building names
    try:
        r2 = requests.get(textsearch_url, params=textsearch_params, timeout=10)
        r2.raise_for_status()
        text_data = r2.json()
        text_results = text_data.get("results", [])
        
        for result in text_results[:5]:
            name = result.get("name", "")
            types = result.get("types", [])
            # Look for residential building names
            if any(keyword in name.lower() for keyword in 
                   ["apartment", "residence", "tower", "condo", "loft", "manor", "villa", "court", "place"]):
                alternative_names.append({
                    "name": name,
                    "types": types,
                    "source": "text_search"
                })
    except Exception:
        pass
    
    if not main_place:
        return {
            "main_place": None,
            "alternative_names": alternative_names,
            "nearby_places": [],
            "distance_tiers": {},
            "address_features": extract_address_features(address),
        }
    
    c = candidates[0]
    loc = c.get("geometry", {}).get("location", {})
    lat, lng = loc.get("lat"), loc.get("lng")
    
    main_place = {
        "name": c.get("name"),
        "formatted_address": c.get("formatted_address"),
        "types": c.get("types", []),
        "business_status": c.get("business_status"),
        "user_ratings_total": c.get("user_ratings_total", 0),
        "rating": c.get("rating"),
        "lat": lat,
        "lng": lng,
    }
    
    c = candidates[0]
    loc = c.get("geometry", {}).get("location", {})
    lat, lng = loc.get("lat"), loc.get("lng")
    
    main_place = {
        "name": c.get("name"),
        "formatted_address": c.get("formatted_address"),
        "types": c.get("types", []),
        "business_status": c.get("business_status"),
        "user_ratings_total": c.get("user_ratings_total", 0),
        "rating": c.get("rating"),
        "lat": lat,
        "lng": lng,
    }
    
    nearby_places = []
    distance_tiers = {
        "exact_match": [],      # 0-5m (same location)
        "same_building": [],    # 5-30m
        "adjacent": [],         # 30-70m
    }
    
    if lat and lng:
        # Nearby search
        nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        nearby_params = {
            "key": GOOGLE_PLACES_API_KEY,
            "location": f"{lat},{lng}",
            "radius": radius_m,
        }
        
        try:
            r2 = requests.get(nearby_url, params=nearby_params, timeout=10)
            r2.raise_for_status()
            nearby_data = r2.json()
            results = nearby_data.get("results", [])
            
            for res in results[:25]:
                rloc = res.get("geometry", {}).get("location", {})
                rlat, rlng = rloc.get("lat"), rloc.get("lng")
                dist = None
                if rlat is not None and rlng is not None:
                    dist = haversine_distance_m(lat, lng, rlat, rlng)
                
                place_info = {
                    "name": res.get("name"),
                    "types": res.get("types", []),
                    "business_status": res.get("business_status"),
                    "user_ratings_total": res.get("user_ratings_total", 0),
                    "distance_m": dist,
                }
                nearby_places.append(place_info)
                
                # Categorize by distance
                if dist is not None:
                    if dist <= 5:
                        distance_tiers["exact_match"].append(place_info)
                    elif dist <= 30:
                        distance_tiers["same_building"].append(place_info)
                    else:
                        distance_tiers["adjacent"].append(place_info)
        except Exception:
            pass
    
    return {
        "main_place": main_place,
        "alternative_names": alternative_names,
        "nearby_places": nearby_places,
        "distance_tiers": distance_tiers,
        "address_features": extract_address_features(address),
    }


REFINED_SYSTEM_PROMPT = """
You are an address classification assistant that determines whether an address is primarily residential or business.

You will receive data about an address including:
- The address text itself
- Information about what's located at that address
- Names of buildings or businesses found there (check both main_place and alternative_names)
- What's nearby (within roughly 30 meters)

Your job is to classify the address as:
- "residential" = homes, apartments, condos, or residential buildings
- "business" = offices, stores, restaurants, banks, or commercial buildings  
- "unknown" = insufficient information to determine confidently

CRITICAL CLASSIFICATION RULES (apply in this order):

1. ADDRESS TEXT - Strongest signal:
   - "Suite", "Ste", "Office", "Floor" + number = BUSINESS (office space)
   - "Apt", "Apartment", "Unit" + number = RESIDENTIAL
   - These override most other signals

2. BUILDING NAMES - Check both main_place name and alternative_names array:
   RESIDENTIAL building names (high priority):
   - Contains: "Apartments", "Residences", "Condos", "Towers", "Lofts", "Village", "Manor", "Court", "Gateway" + residential context
   - Examples: "Shoreline Gateway", "Centurion Apartments", "Ocean Towers", "Pine Avenue Lofts"
   - IF YOU FIND THESE → The building is RESIDENTIAL, even if there are businesses nearby
   
   Important: Many residential buildings have ground-floor retail (restaurants, real estate offices, shops). The presence of these businesses does NOT make the building commercial - it's still a residential building with retail tenants.
   
   BUSINESS building names:
   - Specific business: "Farmers Bank", "Joe's Pizza", "Smith Law Offices"
   - Commercial centers: "Office Plaza", "Business Center", "Professional Building"

3. WHAT'S AT THE ADDRESS:
   - Multiple businesses with no residential building name → Likely BUSINESS
   - Specific business operating at this address → BUSINESS
   - Real estate agency alone is NOT conclusive (could manage residential or commercial)
   - Empty/no businesses + no other indicators → Lean RESIDENTIAL

4. DECISION PRIORITY:
   Residential building name (Apartments/Residences/etc.) ALWAYS indicates RESIDENTIAL, regardless of nearby businesses.
   
   Only classify as BUSINESS if:
   - Suite/Office in address, OR
   - Specific business name identified with no residential building name, OR
   - Multiple businesses present with no residential building name

EXPLANATION STYLE:
Write for business executives in plain language. Do NOT use technical terms like "exact_match tier", "main_place types", "distance_tiers", "address_features", or API field names.

Good examples:
✓ "This is Shoreline Gateway, a residential apartment building. While there are some businesses on the ground floor, the building itself is residential."
✓ "The address includes Suite 2050, indicating office space, and multiple law firms are located here."
✓ "This appears to be a commercial building with several operating businesses including restaurants and offices."

Bad examples:
✗ "The exact_match tier contains operational businesses..."
✗ "Based on address_features.has_suite_office being true..."
✗ "The alternative_names array shows..."

OUTPUT FORMAT:
{
  "category": "residential" | "business" | "unknown",
  "confidence": 0.0-1.0,
  "reason": "Clear explanation (1-2 sentences) in plain business language"
}
"""


def classify_address_improved(address: str, GOOGLE_PLACES_API_KEY: str, client) -> dict:
    """
    Refined classifier focusing on quality over quantity of signals.
    """
    try:
        context = get_place_context(address, GOOGLE_PLACES_API_KEY)
    except Exception as e:
        context = {
            "main_place": None,
            "nearby_places": [],
            "distance_tiers": {},
            "address_features": extract_address_features(address),
            "error": str(e),
        }
    
    # Add original address to context
    context["address"] = address
    
    messages = [
        {"role": "system", "content": REFINED_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Classify this address using the prioritized rules.\n\n"
                f"INPUT:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
                "Return JSON with category, confidence, and reason."
            ),
        },
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
    except Exception as e:
        return {
            "category": "unknown",
            "confidence": 0.0,
            "reason": f"LLM API error: {e}",
        }
    
    category = str(data.get("category", "unknown")).lower()
    if category not in {"residential", "business", "unknown"}:
        category = "unknown"
    
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    
    reason = str(data.get("reason", ""))
    
    # Stricter threshold
    if confidence < 0.65 and category != "unknown":
        category = "unknown"
        reason += " [Low confidence]"
    
    return {
        "category": category,
        "confidence": confidence,
        "reason": reason,
    }

# ---------- FLASK ROUTES ----------

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        if address:
            result = classify_address_smart(address)
            result["address"] = address
    return render_template_string(HTML, result=result)


@app.route("/api/classify", methods=["POST"])
def api_classify():
    data = request.get_json(silent=True) or {}
    address = data.get("address", "").strip()

    if not address:
        return jsonify({"error": "Missing 'address'"}), 400

    result = classify_address_improved(address)
    result["address"] = address
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
