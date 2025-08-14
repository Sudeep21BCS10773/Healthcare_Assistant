import os, uuid, time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import requests

# ----------------- Config -----------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_MESSAGE = (
    "You are a careful, friendly healthcare assistant. "
    "Provide general wellness info, triage-style guidance, and safety-first suggestions. "
    "DO NOT diagnose or prescribe medicines/dosages. "
    "Use plain language and short bullet points when helpful. "
    "ALWAYS: remind to consult a licensed clinician for diagnosis/treatment, "
    "and to seek urgent care for red flags (chest pain, trouble breathing, severe bleeding, "
    "sudden weakness on one side, fainting, high fever in infants). "
    "Consider the user's age, sex, pregnancy, allergies, and chronic conditions when given."
)

# In-memory session store: { session_id: [("user"/"assistant", "text", ts), ...], "profile": {...} }
SESSIONS = {}

FACILITY_TYPES = {
    "hospital": "hospital",
    "pharmacy": "pharmacy",
    "clinic": "doctor",          # Google 'doctor' type approximates clinics
    "lab": "laboratory",         # some regions index as 'laboratory' or 'health' – we’ll fall back
    "emergency": "hospital"      # filtered by 'emergency' keyword
}

def get_session(session_id: str):
    if not session_id or session_id not in SESSIONS:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {"history": [], "profile": {}}
    return session_id, SESSIONS[session_id]

def build_messages(history, profile, user_text):
    context = []
    if profile:
        profile_lines = []
        for k, v in profile.items():
            if v:
                profile_lines.append(f"{k.capitalize()}: {v}")
        if profile_lines:
            context.append("Patient context:\n" + "\n".join(profile_lines))
    if context:
        context_block = {"role": "system", "content": "\n\n".join(context)}
    else:
        context_block = None

    msgs = [{"role": "system", "content": SYSTEM_MESSAGE}]
    if context_block:
        msgs.append(context_block)
    for (role, content, _ts) in history[-8:]:
        msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": user_text})
    return msgs

def openai_reply(messages):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",      # upgrade to "gpt-4o" for higher quality
        messages=messages,
        temperature=0.4,
        max_tokens=450,
    )
    return completion.choices[0].message.content.strip()

# ----------------- Routes -----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/session", methods=["POST"])
def bootstrap_session():
    """
    Create/restore a session. Optionally update profile (age, sex, pregnancy, allergies, conditions).
    """
    data = request.get_json(force=True) or {}
    session_id = data.get("session_id")
    session_id, sess = get_session(session_id)

    # Save/merge profile
    profile = sess.get("profile", {})
    for key in ["name", "age", "sex", "pregnant", "allergies", "conditions"]:
        if data.get(key) is not None:
            profile[key] = data.get(key)
    sess["profile"] = profile

    return jsonify({"session_id": session_id, "profile": profile})

@app.route("/chat", methods=["POST"])
def chat():
    """
    POST { session_id, message }
    """
    data = request.get_json(force=True) or {}
    session_id = data.get("session_id")
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    session_id, sess = get_session(session_id)
    ts = int(time.time())
    sess["history"].append(("user", user_msg, ts))

    try:
        messages = build_messages(sess["history"], sess.get("profile", {}), user_msg)
        bot = openai_reply(messages)
        footer = ("\n\n—\nThis assistant is not a doctor. For diagnosis or treatment, "
                  "consult a licensed clinician. Seek emergency care for red-flag symptoms.")
        bot_safe = f"{bot}{footer}"
        sess["history"].append(("assistant", bot_safe, int(time.time())))
        return jsonify({"session_id": session_id, "reply": bot_safe, "timestamp": ts})
    except Exception as e:
        err = f"Sorry, I hit an error: {e}"
        sess["history"].append(("assistant", err, int(time.time())))
        return jsonify({"session_id": session_id, "reply": err}), 500

@app.route("/history", methods=["GET"])
def history():
    session_id = request.args.get("session_id")
    if not session_id or session_id not in SESSIONS:
        return jsonify({"history": []})
    return jsonify({"history": SESSIONS[session_id]["history"], "profile": SESSIONS[session_id].get("profile", {})})

# ------------- Facilities (Google Places) -------------
def google_places_nearby(lat, lng, type_key, keyword=None, radius=5000):
    """
    Wraps Google Places Nearby Search.
    """
    gtype = FACILITY_TYPES.get(type_key, "hospital")
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": GOOGLE_MAPS_API_KEY,
        "location": f"{lat},{lng}",
        "radius": radius,  # meters
        "type": gtype,
    }
    if keyword:
        params["keyword"] = keyword

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    results = []
    for p in data.get("results", [])[:20]:
        results.append({
            "name": p.get("name"),
            "address": p.get("vicinity") or p.get("formatted_address"),
            "rating": p.get("rating"),
            "user_ratings_total": p.get("user_ratings_total"),
            "open_now": p.get("opening_hours", {}).get("open_now"),
            "lat": p.get("geometry", {}).get("location", {}).get("lat"),
            "lng": p.get("geometry", {}).get("location", {}).get("lng"),
            "place_id": p.get("place_id"),
        })
    return results

@app.route("/facilities", methods=["GET"])
def facilities():
    """
    /facilities?type=hospital|pharmacy|clinic|lab|emergency&lat=..&lng=..&radius=5000
    """
    if not GOOGLE_MAPS_API_KEY:
        return jsonify({"error": "GOOGLE_MAPS_API_KEY not set"}), 500

    type_key = (request.args.get("type") or "hospital").lower()
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    radius = int(request.args.get("radius") or 5000)

    if not (lat and lng):
        return jsonify({"error": "lat and lng are required"}), 400

    keyword = None
    if type_key == "emergency":
        keyword = "emergency"

    try:
        results = google_places_nearby(lat, lng, type_key, keyword=keyword, radius=radius)
        return jsonify({"type": type_key, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY is not set. Chat will fail.")
    if not GOOGLE_MAPS_API_KEY:
        print("WARNING: GOOGLE_MAPS_API_KEY is not set. Facilities lookup will fail.")
    app.run(debug=True)
