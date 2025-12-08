import os
import math
import json
import requests
from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI

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
    R = 6371000  # Earth radius in m
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_place_context(address: str, radius_m: int = 40) -> dict:
    """
    1) Find main place (the address) via Find Place From Text, with geometry.
    2) Use Nearby Search around that location to get nearby POIs.
    Returns a dict with main_place + a small list of nearby_places.
    """
    if not GOOGLE_PLACES_API_KEY:
        raise RuntimeError("GOOGLE_PLACES_API_KEY environment variable is not set")

    # Step 1: Find Place
    find_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    find_params = {
        "key": GOOGLE_PLACES_API_KEY,
        "input": address,
        "inputtype": "textquery",
        "fields": "name,formatted_address,types,business_status,user_ratings_total,geometry",
    }
    r = requests.get(find_url, params=find_params, timeout=10)
    r.raise_for_status()
    data = r.json()

    candidates = data.get("candidates", [])
    if not candidates:
        return {
            "main_place": None,
            "nearby_places": [],
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
        "lat": lat,
        "lng": lng,
    }

    # If no lat/lng, we can't do Nearby
    if lat is None or lng is None:
        return {
            "main_place": main_place,
            "nearby_places": [],
        }

    # Step 2: Nearby Search
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    nearby_params = {
        "key": GOOGLE_PLACES_API_KEY,
        "location": f"{lat},{lng}",
        "radius": radius_m,
    }
    r2 = requests.get(nearby_url, params=nearby_params, timeout=10)
    r2.raise_for_status()
    nearby_data = r2.json()
    results = nearby_data.get("results", [])

    nearby_places = []
    for res in results[:10]:  # limit to top 10
        rloc = res.get("geometry", {}).get("location", {})
        rlat, rlng = rloc.get("lat"), rloc.get("lng")
        dist = None
        if rlat is not None and rlng is not None:
            dist = haversine_distance_m(lat, lng, rlat, rlng)

        nearby_places.append({
            "name": res.get("name"),
            "types": res.get("types", []),
            "business_status": res.get("business_status"),
            "user_ratings_total": res.get("user_ratings_total", 0),
            "distance_m": dist,
        })

    return {
        "main_place": main_place,
        "nearby_places": nearby_places,
    }


SYSTEM_PROMPT = """
You are an address classification assistant.

You will receive a JSON object with:
- "address": the raw address string.
- "main_place": information about the address from Google Places (may be null), with keys:
    - name, formatted_address, types, business_status, user_ratings_total, lat, lng
- "nearby_places": a list of nearby Google Places results within a small radius, each with:
    - name, types, business_status, user_ratings_total, distance_m

Your job is to classify the address property itself into one of:
- "residential"  = primarily a home or apartment building
- "business"     = primarily used by businesses (offices, shops, restaurants, banks, coworking, etc.)
- "unknown"      = you cannot reliably infer if it is residential or business.

Guidelines:

1) Use the ADDRESS TEXT:
- Suite/floor/room tokens like "Ste 2050", "Suite 300", "Floor 5" usually indicate business offices.
- PO Boxes, mail centers, UPS/FedEx Stores, virtual offices are business.
- Apartment-style tokens such as "Apt", "Apartment", "Unit", "#", or words like "Apartments", "Residences",
  "Condos", "Student Housing" suggest residential.

2) Use MAIN_PLACE:
- If types include clearly business categories (e.g., "bank", "store", "restaurant", "gym", "real_estate_agency",
  "lawyer", "accounting", "insurance_agency", "cafe", "coworking_space", "shopping_mall", "hospital",
  "school", "university", "local_government_office", "lodging") OR there is a non-null business_status
  or user_ratings_total > 0, this is strong evidence of business use.
- Types like "premise" or "subpremise" alone are neutral and do NOT prove residential or business.

3) Use NEARBY_PLACES:
- If there are many distinct businesses (restaurants, bars, shops, offices, banks, etc.) within ~30–40 meters,
  especially sharing the same or very similar address, it strongly suggests a commercial or mixed-use building.
- If there are zero or almost no POIs within that small radius, it is more likely a purely residential property.
- A single corner cafe nearby is not enough by itself to call the property a business; focus on patterns and density.

4) Decision:
- If evidence strongly favors business, choose "business".
- If evidence strongly favors residential, choose "residential".
- If the evidence is mixed or weak and you cannot be reasonably confident, choose "unknown".

Output:
Return a single JSON object:

{
  "category": "residential" | "business" | "unknown",
  "confidence": float between 0 and 1,
  "reason": "very short explanation (1–2 sentences)"
}
"""


def classify_address_smart(address: str) -> dict:
    """
    Classify address using:
    - main_place (Find Place)
    - nearby_places (Nearby Search)
    - LLM reasoning over the full context.
    Always returns {category, confidence, reason, nearby_count}.
    """
    try:
        place_context = get_place_context(address)
    except Exception as e:
        place_context = {
            "main_place": None,
            "nearby_places": [],
            "error": str(e),
        }

    context = {
        "address": address,
        "main_place": place_context.get("main_place"),
        "nearby_places": place_context.get("nearby_places", []),
        "error": place_context.get("error"),
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Classify this address using the full context below.\n\n"
                f"INPUT JSON:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
                "Return ONLY the JSON object."
            ),
        },
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
    except Exception as e:
        data = {
            "category": "unknown",
            "confidence": 0.0,
            "reason": f"Error calling LLM API or parsing JSON: {e}",
        }

    category = str(data.get("category", "unknown")).lower()
    if category not in {"residential", "business", "unknown"}:
        category = "unknown"

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    reason = str(data.get("reason", ""))

    # Optional threshold
    if confidence < 0.6 and category != "unknown":
        category = "unknown"

    return {
        "category": category,
        "confidence": confidence,
        "reason": reason,
        "nearby_count": len(context.get("nearby_places", [])),
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

    result = classify_address_smart(address)
    result["address"] = address
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
