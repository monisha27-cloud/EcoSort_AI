"""
app.py
------
EcoSort AI backend - a Flask REST API sitting on top of a SQLite database
built from the 1M1B "Eco-Sort" campus waste dataset.

Endpoints
---------
GET  /api/items                 list / search / filter the catalog
GET  /api/items/<record_id>     get a single item by id
GET  /api/categories            distinct list of categories
GET  /api/locations             distinct list of campus locations
GET  /api/stats                 aggregate numbers for the dashboard
POST /api/lookup                take a CV label (or free-text name) and
                                 return the best-matching catalog item,
                                 logging the scan
GET  /api/scan-logs             recent scan history (for the dashboard)

Run with:  python app.py   (serves on http://localhost:5000)
"""

from flask import Flask, jsonify, request

from database import get_connection, init_db
from cv_mapping import LABEL_TO_ITEM

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    # Manual CORS (no extra dependency needed) so the static frontend,
    # served from a different origin/port, can call this API.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def cors_preflight(_any):
    return "", 204


# ---------------------------------------------------------------- helpers --
def row_to_dict(row):
    return {k: row[k] for k in row.keys()}


def find_best_item_match(name_guess, cur):
    """Very small fuzzy matcher: exact (case-insensitive) match first,
    then substring match, then None."""
    name_guess = (name_guess or "").strip().lower()
    if not name_guess:
        return None

    cur.execute("SELECT * FROM items WHERE LOWER(item) = ?", (name_guess,))
    row = cur.fetchone()
    if row:
        return row

    cur.execute(
        "SELECT * FROM items WHERE LOWER(item) LIKE ? LIMIT 1",
        (f"%{name_guess}%",),
    )
    row = cur.fetchone()
    return row


# ------------------------------------------------------------------ items --
@app.route("/api/items", methods=["GET"])
def list_items():
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM items WHERE 1=1"
    params = []

    search = request.args.get("search")
    category = request.args.get("category")
    hazard_level = request.args.get("hazard_level")
    recyclable = request.args.get("recyclable")
    e_waste = request.args.get("e_waste")
    campus_location = request.args.get("campus_location")

    if search:
        query += " AND LOWER(item) LIKE ?"
        params.append(f"%{search.lower()}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    if hazard_level:
        query += " AND hazard_level = ?"
        params.append(hazard_level)
    if recyclable:
        query += " AND recyclable = ?"
        params.append(recyclable)
    if e_waste:
        query += " AND e_waste = ?"
        params.append(e_waste)
    if campus_location:
        query += " AND campus_location = ?"
        params.append(campus_location)

    query += " ORDER BY record_id ASC"

    cur.execute(query, params)
    rows = [row_to_dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"count": len(rows), "items": rows})


@app.route("/api/items/<int:record_id>", methods=["GET"])
def get_item(record_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE record_id = ?", (record_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/api/categories", methods=["GET"])
def categories():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM items ORDER BY category")
    values = [r["category"] for r in cur.fetchall()]
    conn.close()
    return jsonify(values)


@app.route("/api/locations", methods=["GET"])
def locations():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT campus_location FROM items ORDER BY campus_location"
    )
    values = [r["campus_location"] for r in cur.fetchall()]
    conn.close()
    return jsonify(values)


# ------------------------------------------------------------------ stats --
@app.route("/api/stats", methods=["GET"])
def stats():
    conn = get_connection()
    cur = conn.cursor()

    def agg(col):
        cur.execute(f"SELECT {col} AS k, COUNT(*) AS c FROM items GROUP BY {col}")
        return {r["k"]: r["c"] for r in cur.fetchall()}

    cur.execute("SELECT COUNT(*) AS c FROM items")
    total_items = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM scan_logs")
    total_scans = cur.fetchone()["c"]

    data = {
        "total_items": total_items,
        "total_scans": total_scans,
        "by_category": agg("category"),
        "by_hazard_level": agg("hazard_level"),
        "by_recyclable": agg("recyclable"),
        "by_e_waste": agg("e_waste"),
        "by_campus_location": agg("campus_location"),
    }
    conn.close()
    return jsonify(data)


# ---------------------------------------------------------------- lookup --
@app.route("/api/lookup", methods=["POST"])
def lookup():
    """
    Body JSON: { "label": "<cv model output>", "confidence": 0.87, "source": "camera" }
    The label may be a raw ImageNet/MobileNet class (e.g. "notebook, laptop")
    or a free-text search typed by the user. We map it to one of our 25
    catalog items using cv_mapping.LABEL_TO_ITEM, then fall back to a fuzzy
    DB match, log the scan, and return the disposal instructions.
    """
    payload = request.get_json(silent=True) or {}
    raw_label = payload.get("label", "")
    confidence = payload.get("confidence")
    source = payload.get("source", "camera")

    conn = get_connection()
    cur = conn.cursor()

    # 1) try the curated CV-label -> item mapping (best for camera scans)
    mapped_item_name = None
    label_lower = raw_label.lower()
    for key, item_name in LABEL_TO_ITEM.items():
        if key in label_lower:
            mapped_item_name = item_name
            break

    row = None
    if mapped_item_name:
        row = find_best_item_match(mapped_item_name, cur)

    # 2) fall back to matching the raw label / search text directly
    if row is None:
        row = find_best_item_match(raw_label, cur)

    result = row_to_dict(row) if row else None

    cur.execute(
        """
        INSERT INTO scan_logs (source, predicted_label, confidence, matched_item, matched_record_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            source,
            raw_label,
            confidence,
            result["item"] if result else None,
            result["record_id"] if result else None,
        ),
    )
    conn.commit()
    conn.close()

    if result is None:
        return jsonify(
            {
                "matched": False,
                "raw_label": raw_label,
                "message": "Couldn't confidently match this to an item in the catalog. "
                           "Try searching manually, or dispose of it as General Waste "
                           "if unsure, and flag it for review.",
            }
        )

    return jsonify({"matched": True, "raw_label": raw_label, "item": result})


@app.route("/api/scan-logs", methods=["GET"])
def scan_logs():
    limit = int(request.args.get("limit", 20))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM scan_logs ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = [row_to_dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# Seed the database as soon as the module is imported - this runs both
# with `python app.py` locally AND when a production server like gunicorn
# imports `app:app` on a host such as Render/Railway.
init_db()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
