"""supportbot self-check: uv run python checks.py  (exit 0 = pass)"""
import pathlib
import sys
import tempfile

fails = 0


def ok(cond, msg):
    global fails
    if cond:
        print(f"  ok: {msg}")
    else:
        fails += 1
        print(f"FAIL: {msg}")


# isolate the whole check run in a temp DB before importing anything that uses it
import db  # noqa: E402

db.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "check.db"
db.init()

import kb  # noqa: E402
import pipeline  # noqa: E402

print("[1] chunking")
text = "Short para.\n\n" + ("Sentence one. " * 120) + "\n\nTail para."
chunks = kb.chunk_text(text)
ok(len(chunks) == 4, f"paragraph split + hard split of oversized para (got {len(chunks)})")
ok(all(len(c) <= 1200 for c in chunks), "no chunk exceeds max_chars")
ok(kb.chunk_text("") == [], "empty text -> []")

print("[2] FTS5 index + retrieve")
ok(kb.match_query("How long do refunds take??") == '"long"* OR "refunds"* OR "take"*',
   "stopwords dropped, punctuation safe, prefix-matched")
ok(kb.match_query("is it a") == "", "all-stopword question -> empty query")
with db.get() as con:
    kb.index_document(con, "Shipping", "Standard shipping takes 3 to 5 business days.")
    kb.index_document(con, "Refunds", "Refunds are issued within 5 business days of the scan.")
    hits = kb.search(con, "refunds issued scan payment", limit=2)
    ok(hits and hits[0]["doc"] == "Refunds", f"bm25 ranks the refund chunk first ({[h['doc'] for h in hits]})")
    ok("Refunds" in [h["doc"] for h in kb.search(con, "how long does a refund take")],
       "refund question retrieves the refund chunk")
    ok(kb.search(con, "zzzq plugh xyzzy") == [], "unknown topic -> no crash, no hits")
    ok(kb.search(con, "the and of") == [], "stopword-only question -> []")

print("[3] critic / confidence score")
sources = ["Refunds are issued to the original payment method within 5 business days."]
grounded = pipeline.critic(sources[0] + " [1]", sources)
ok(grounded["score"] == 1.0, f"verbatim quote scores 1.0 (got {grounded['score']})")
ok(grounded["sentences"][0]["supported"] is True, "sentence marked supported")
invented = pipeline.critic("Refunds take 30 days and cost a 15 percent restocking fee.", sources)
ok(invented["score"] < 0.5, f"invented policy scores low (got {invented['score']})")
ok(invented["sentences"][0]["supported"] is False, "invented sentence marked unsupported")
mixed = pipeline.critic(sources[0] + " We also pay you 100 dollars cash.", sources)
ok(0.4 < mixed["score"] < 1.0, f"half-grounded draft scores in between (got {mixed['score']})")
short = pipeline.critic("Thanks!", sources)
ok(short["score"] == 0.0 and short["sentences"][0]["supported"] is None,
   "short greeting is shown but not scored")
ok(pipeline.critic("anything at all here", [])["score"] == 0.0, "no sources -> score 0")

print("[4] status routing")
ok(pipeline.status_for(1.0, 0.6, 2) == "ready", "1.0 + sources -> ready")
ok(pipeline.status_for(0.5, 0.6, 2) == "low_confidence", "0.5 -> low_confidence")
ok(pipeline.status_for(0.1, 0.6, 2) == "needs_human", "0.1 -> needs_human")
ok(pipeline.status_for(1.0, 0.6, 0) == "needs_human", "no sources -> needs_human (gap logged)")
ok(pipeline.quoted_answer([]).startswith("I couldn't find anything"), "empty KB -> honest no-answer")

print("[5] triage tagging")
ok(pipeline.categorize("I was charged twice, refund please") == "billing", "billing detected")
ok(pipeline.categorize("the item arrived damaged, I want to exchange") == "return", "return detected")
ok(pipeline.categorize("can't log in after password reset") == "bug", "bug detected")
ok(pipeline.categorize("do you gift wrap") == "general", "general fallback")
ok(pipeline.urgency("charged twice, this is urgent") == "high", "urgent flagged")
ok(pipeline.urgency("just wondering about sizing") == "normal", "normal stays normal")

print("[6] end-to-end: index -> ticket -> draft -> status")
import app as web  # noqa: E402

client = web.app.test_client()
client.post("/knowledge", data={"sample": "1"})
r = client.post("/tickets", data={"body": "My package arrived damaged, can I get a replacement?"})
ok(r.status_code == 302, "POST /tickets redirects to the thread")
with db.get() as con:
    tid = con.execute("SELECT MAX(id) id FROM tickets").fetchone()["id"]
result = pipeline.process(tid)
ok(result["status"] == "ready", f"damaged-item ticket drafted as ready ({result})")
with db.get() as con:
    row = con.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
ok(row["n_sources"] > 0, "sources retrieved for the ticket")
ok(row["confidence"] == 1.0, "keyless template draft is 100% grounded (verbatim quote)")
ok("[1]" in row["draft"], "draft carries a citation")
gap = client.post("/tickets", data={"body": "Where is your Tokyo retail showroom located?"})
with db.get() as con:
    gid = con.execute("SELECT MAX(id) id FROM tickets").fetchone()["id"]
pipeline.process(gid)
with db.get() as con:
    grow = con.execute("SELECT * FROM tickets WHERE id=?", (gid,)).fetchone()
ok(grow["status"] == "needs_human" and grow["n_sources"] == 0,
   f"unanswerable question routed to human + gap logged ({grow['status']}/{grow['n_sources']})")
client.post(f"/tickets/{tid}/review", data={"action": "approve", "reply": "Yes — replacement shipped."})
with db.get() as con:
    ok(con.execute("SELECT status FROM tickets WHERE id=?", (tid,)).fetchone()["status"] == "approved",
       "approve sets status")

print("[7] no hardcoded credentials / foreign LLM callers")
bad, llm = [], []
for f in pathlib.Path(__file__).parent.glob("*.py"):
    if f.name == "checks.py":
        continue
    src = f.read_text(encoding="utf8")
    for i, line in enumerate(src.splitlines(), 1):
        if "sk-" in line or "Authorization: Bearer" in line:
            bad.append(f"{f.name}:{i}")
    if f.name != "ai.py" and ("chat/completions" in src or "openai" in src.lower()):
        llm.append(f.name)
ok(not bad, f"no keys in source ({bad})")
ok(not llm, f"LLM endpoint only in ai.py ({llm})")
import ai as ai_mod  # noqa: E402

ok(ai_mod.config()["api_key"] == "" or ai_mod.config()["api_key"].startswith("sk-") is False,
   "ai.config() reads the key at runtime only (env/settings)")
ok(ai_mod.generate("support_reply", {"question": "q", "chunks": []}) != "",
   "keyless generate() falls back to a real template draft, never ''")

print()
sys.exit(1 if fails else 0)
