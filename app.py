"""supportbot — grounded support drafts + non-LLM critic + human inbox.
Run: uv run flask --app app run
"""
import json

import db
import jobs
import kb
from flask import (Flask, jsonify, redirect, render_template, request, url_for)

app = Flask(__name__)
db.init()

STATUSES = ("ready", "low_confidence", "needs_human", "approved", "processing", "rejected")

SAMPLE_FAQ = """Shipping and delivery
Standard shipping inside the United States takes 3 to 5 business days and is free on orders over 50 dollars. Express shipping costs 19 dollars and arrives in 2 business days. We ship to Canada and the United Kingdom; Canadian orders arrive in 7 to 10 business days.

Returns and exchanges
Unused items can be returned within 30 days of delivery for a full refund. Start a return from the Orders page and we email a prepaid label. Items marked final sale cannot be returned. Exchanges ship free once the original item is scanned by the carrier.

Refunds
Refunds are issued to the original payment method within 5 business days after the warehouse scans the returned item. Shipping charges are not refunded. Store credit is offered instantly if you prefer not to wait.

Damaged or wrong items
If an item arrives damaged or is not what you ordered, send a photo through the Orders page within 14 days. We ship a replacement the same day and you keep the damaged item. No return label is required for damaged goods.

Billing and duplicate charges
Orders are authorized when placed and charged when they ship. A pending authorization can look like a duplicate charge and disappears within 3 business days. If a real duplicate charge appears, email billing with the order number and we refund it within 2 business days.

Account access
Password reset links are valid for 60 minutes. If the email does not arrive, check spam and then request a new link. Accounts lock for 15 minutes after five failed sign-in attempts."""

SAMPLE_TICKETS = (
    "I was charged twice for order #10432, please refund me asap.",
    "My package arrived damaged, the screen is cracked. Can I get a new one?",
    "How long does a refund take after I send something back?",
    "Do you offer gift wrapping with a handwritten note?",
)


# --- pages ---------------------------------------------------------------

@app.get("/")
def index():
    status = request.args.get("status", "")
    with db.get() as con:
        if status == "gaps":
            where, args = "WHERE n_sources = 0", ()
        elif status in STATUSES:
            where, args = "WHERE status = ?", (status,)
        else:
            where, args = "", ()
        tickets = con.execute(
            f"SELECT * FROM tickets {where} ORDER BY id DESC LIMIT 200", args
        ).fetchall()
        counts = dict(con.execute(
            "SELECT status, COUNT(*) FROM tickets GROUP BY status").fetchall())
        gaps = con.execute("SELECT COUNT(*) c FROM tickets WHERE n_sources = 0").fetchone()["c"]
        docs = con.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM chunks c WHERE c.doc_id = d.id) AS n "
            "FROM docs d ORDER BY d.id DESC").fetchall()
    return render_template("index.html", tickets=tickets, status=status, counts=counts,
                           gaps=gaps, docs=docs)


@app.get("/tickets/<int:ticket_id>")
def ticket(ticket_id: int):
    with db.get() as con:
        t = con.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if t is None:
        return redirect(url_for("index"))
    return render_template("ticket.html", t=t, citations=json.loads(t["citations"]),
                           critic=json.loads(t["critic"]))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    keys = ("ai_base_url", "ai_api_key", "ai_model", "min_confidence")
    if request.method == "POST":
        with db.get() as con:
            for k in keys:
                if k not in request.form:
                    continue
                v = request.form[k].strip()
                if k == "ai_api_key" and not v:  # blank = keep the saved key
                    continue
                db.set_setting(con, k, v)
        return redirect(url_for("index"))
    with db.get() as con:
        vals = {k: db.get_setting(con, k) for k in keys}
        saved = bool(db.get_setting(con, "ai_api_key"))
    return render_template("settings.html", s=vals, key_saved=saved)


@app.route("/knowledge", methods=["GET", "POST"])
def knowledge():
    if request.method == "POST":
        title, text = "", ""
        up = request.files.get("file")
        if up and up.filename:
            title = up.filename
            text = up.read().decode("utf-8", "replace")
        elif request.form.get("sample"):
            title, text = "Sample store FAQ", SAMPLE_FAQ
        else:
            title = request.form.get("title", "").strip()
            text = request.form.get("text", "")
        if not (text or "").strip():
            return redirect(url_for("knowledge"))
        with db.get() as con:
            info = kb.index_document(con, title or "pasted policy", text)
        return redirect(url_for("knowledge", added=info["chunks"]))
    with db.get() as con:
        docs = con.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM chunks c WHERE c.doc_id = d.id) AS n "
            "FROM docs d ORDER BY d.id DESC").fetchall()
    return render_template("knowledge.html", docs=docs,
                           added=request.args.get("added", type=int))


# --- actions (json) ------------------------------------------------------

@app.post("/tickets")
def create_ticket():
    body = (request.get_json(silent=True) or request.form).get("body", "").strip()
    if not body:
        return jsonify(ok=False, msg="Empty message"), 400
    subject = (request.get_json(silent=True) or request.form).get("subject", "").strip()
    with db.get() as con:
        ticket_id = con.execute("INSERT INTO tickets(subject, body) VALUES(?,?)",
                                (subject, body)).lastrowid
    jobs.enqueue(ticket_id)
    if request.is_json:
        return jsonify(ok=True, ticket_id=ticket_id)
    return redirect(url_for("ticket", ticket_id=ticket_id))


@app.get("/tickets/<int:ticket_id>.json")
def ticket_json(ticket_id: int):
    with db.get() as con:
        t = con.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if t is None:
        return jsonify(ok=False), 404
    return jsonify(ok=True, status=t["status"], confidence=t["confidence"],
                   category=t["category"], urgency=t["urgency"],
                   sentiment=t["sentiment"], n_sources=t["n_sources"])


@app.post("/tickets/<int:ticket_id>/review")
def review(ticket_id: int):
    action = request.form.get("action", "approve")
    text = request.form.get("reply", "").strip()
    status = {"approve": "approved", "reject": "rejected", "save": "low_confidence"}.get(
        action, "ready")
    with db.get() as con:
        t = con.execute("SELECT draft FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if t is None:
            return jsonify(ok=False, msg="no such ticket"), 404
        con.execute("UPDATE tickets SET status=?, reply=? WHERE id=?",
                    (status, text or t["draft"], ticket_id))
    return jsonify(ok=True, msg=f"ticket {ticket_id} → {status}")


@app.post("/tickets/<int:ticket_id>/rerun")
def rerun(ticket_id: int):
    with db.get() as con:
        con.execute("UPDATE tickets SET status='processing' WHERE id=?", (ticket_id,))
    jobs.enqueue(ticket_id)
    return jsonify(ok=True, msg="re-running triage")


@app.post("/tickets/sample")
def sample_tickets():
    with db.get() as con:
        for body in SAMPLE_TICKETS:
            jobs.enqueue(con.execute(
                "INSERT INTO tickets(body) VALUES(?)", (body,)).lastrowid)
    return jsonify(ok=True, msg=f"{len(SAMPLE_TICKETS)} sample tickets queued")


@app.post("/settings/test")
def test_ai():
    import ai

    return jsonify(ai.test_connection())


@app.get("/status")
def status():
    with db.get() as con:
        counts = dict(con.execute(
            "SELECT status, COUNT(*) FROM tickets GROUP BY status").fetchall())
    return jsonify(counts=counts, processing=counts.get("processing", 0))


jobs.start_worker()  # 'flask --app app run' never hits __main__
