import os, re, sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "civic.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
os.makedirs(UPLOAD_DIR, exist_ok=True)

CATEGORY_KEYWORDS = {
    "Road Damage": ["pothole", "road", "street", "crack", "damaged road"],
    "Waterlogging": ["waterlogging", "flood", "flooded", "water", "drain", "blocked drain"],
    "Waste Management": ["garbage", "waste", "rubbish", "trash", "bin", "overflowing"],
    "Streetlight": ["streetlight", "street light", "lamp", "dark", "light not working"],
    "Public Safety": ["accident", "danger", "open manhole", "electric wire", "fire", "collapse"],
}

URGENT_WORDS = ["accident", "fire", "electric wire", "open manhole", "injury", "collapse", "danger", "urgent"]
HIGH_WORDS = ["flood", "waterlogging", "blocked drain", "overflowing", "large pothole", "no streetlight"]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citizen_name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                image TEXT,
                summary TEXT NOT NULL,
                priority TEXT NOT NULL,
                priority_score INTEGER NOT NULL,
                priority_reason TEXT NOT NULL,
                duplicate_of INTEGER,
                status TEXT NOT NULL DEFAULT 'Submitted',
                assigned_to TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.commit()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_complaint(description, chosen_category, location, db):
    """Transparent keyword-based AI-style baseline. Not a trained ML model."""
    text = description.lower()
    category = chosen_category
    if not category or category == "Auto Detect":
        scores = {}
        for cat, words in CATEGORY_KEYWORDS.items():
            scores[cat] = sum(1 for word in words if word in text)
        category = max(scores, key=scores.get) if max(scores.values(), default=0) else "Other"

    summary = re.sub(r"\s+", " ", description).strip()
    if len(summary) > 135:
        summary = summary[:132].rsplit(" ", 1)[0] + "..."

    score = 20
    reasons = ["Base score: 20"]
    if any(word in text for word in URGENT_WORDS):
        score += 55
        reasons.append("urgent safety-related keyword detected (+55)")
    elif any(word in text for word in HIGH_WORDS):
        score += 35
        reasons.append("high-impact service issue detected (+35)")
    else:
        reasons.append("no urgent keyword detected")

    if category in ("Public Safety", "Waterlogging"):
        score += 10
        reasons.append(f"{category} can affect public safety (+10)")
    if len(description) > 100:
        score += 5
        reasons.append("detailed description provided (+5)")
    score = min(score, 100)

    if score >= 80:
        priority = "Critical"
    elif score >= 60:
        priority = "High"
    elif score >= 40:
        priority = "Medium"
    else:
        priority = "Low"

    duplicate = None
    rows = db.execute("SELECT id, description, location FROM complaints ORDER BY id DESC LIMIT 200").fetchall()
    for row in rows:
        similarity = SequenceMatcher(None, re.sub(r"\W+", " ", text), re.sub(r"\W+", " ", row["description"].lower())).ratio()
        same_location = location.strip().lower() == (row["location"] or "").strip().lower()
        if similarity >= 0.72 or (same_location and similarity >= 0.55):
            duplicate = row["id"]
            break

    return category, summary, priority, score, "; ".join(reasons), duplicate

@app.route("/")
def index():
    with get_db() as db:
        stats = {
            "total": db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0],
            "pending": db.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('Submitted','Under Review','Assigned')").fetchone()[0],
            "high": db.execute("SELECT COUNT(*) FROM complaints WHERE priority IN ('High','Critical')").fetchone()[0],
            "resolved": db.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0],
        }
        recent = db.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 6").fetchall()
        category_rows = db.execute("SELECT category, COUNT(*) AS count FROM complaints GROUP BY category").fetchall()
        hotspots = db.execute("SELECT location, COUNT(*) AS count FROM complaints GROUP BY lower(location) ORDER BY count DESC LIMIT 5").fetchall()
    return render_template("index.html", stats=stats, recent=recent, category_rows=category_rows, hotspots=hotspots)

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("citizen_name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Auto Detect")
        location = request.form.get("location", "").strip()
        lat = request.form.get("latitude") or None
        lon = request.form.get("longitude") or None
        if not name or not description or not location:
            flash("Please fill in your name, description and location.", "error")
            return redirect(url_for("report"))

        image_name = None
        uploaded = request.files.get("image")
        if uploaded and uploaded.filename:
            if not allowed_file(uploaded.filename):
                flash("Image must be PNG, JPG, JPEG, GIF or WEBP.", "error")
                return redirect(url_for("report"))
            safe_name = secure_filename(uploaded.filename)
            image_name = datetime.now().strftime("%Y%m%d%H%M%S%f") + "_" + safe_name
            uploaded.save(os.path.join(app.config["UPLOAD_FOLDER"], image_name))

        with get_db() as db:
            analyzed = analyze_complaint(description, category, location, db)
            category, summary, priority, score, reason, duplicate = analyzed
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = db.execute("""
                INSERT INTO complaints
                (citizen_name, description, category, location, latitude, longitude, image,
                 summary, priority, priority_score, priority_reason, duplicate_of, status,
                 assigned_to, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', '', ?, ?)
            """, (name, description, category, location, lat, lon, image_name,
                  summary, priority, score, reason, duplicate, now, now))
            complaint_id = cur.lastrowid
            db.commit()
        flash(f"Complaint submitted successfully! Your tracking ID is #{complaint_id}.", "success")
        return redirect(url_for("track", complaint_id=complaint_id))
    return render_template("report.html")

@app.route("/track", methods=["GET", "POST"])
def track_form():
    if request.method == "POST":
        return redirect(url_for("track", complaint_id=request.form.get("complaint_id", "").strip()))
    return render_template("track_form.html")

@app.route("/track/<int:complaint_id>")
def track(complaint_id):
    with get_db() as db:
        complaint = db.execute("SELECT * FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    if not complaint:
        flash("No complaint found with that tracking ID.", "error")
        return redirect(url_for("track_form"))
    return render_template("track.html", complaint=complaint)

@app.route("/admin")
def admin():
    with get_db() as db:
        complaints = db.execute("SELECT * FROM complaints ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, id DESC").fetchall()
    return render_template("admin.html", complaints=complaints)

@app.route("/admin/update/<int:complaint_id>", methods=["POST"])
def update_complaint(complaint_id):
    status = request.form.get("status", "Submitted")
    assigned_to = request.form.get("assigned_to", "").strip()
    allowed_status = {"Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Rejected"}
    if status not in allowed_status:
        flash("Invalid status.", "error")
        return redirect(url_for("admin"))
    with get_db() as db:
        db.execute("UPDATE complaints SET status=?, assigned_to=?, updated_at=? WHERE id=?",
                   (status, assigned_to, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), complaint_id))
        db.commit()
    flash(f"Complaint #{complaint_id} updated.", "success")
    return redirect(url_for("admin"))

@app.route("/api/complaints")
def api_complaints():
    with get_db() as db:
        rows = db.execute("SELECT id, category, location, latitude, longitude, priority, status FROM complaints WHERE latitude IS NOT NULL AND longitude IS NOT NULL").fetchall()
    return jsonify([dict(row) for row in rows])

@app.errorhandler(413)
def too_large(_):
    flash("Image is too large. Maximum size is 5 MB.", "error")
    return redirect(url_for("report"))

init_db()

if __name__ == "__main__":
    app.run(debug=True)
