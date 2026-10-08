"""Triage pipeline.

Pure (checks.py tests these): categorize, urgency, sentiment, critic,
quoted_answer, status_for, sentences, words, ngrams.
IO: process (one DB read/write + optional LLM call through ai.generate only).

Critic is NON-LLM (BUILD §3.5): score = fraction of draft sentences whose
4-grams mostly appear in the retrieved source chunks.
"""
import json
import re

import db
import kb

CATEGORY_RULES = (
    ("billing", ("refund", "invoice", "charge", "charged", "billing", "payment",
                 "subscription", "card", "receipt", "price", "cancel my plan")),
    ("return", ("return", "exchange", "send back", "rma", "ship back", "damaged",
                "wrong item", "warranty")),
    ("bug", ("error", "bug", "crash", "broken", "not working", "doesn't work",
             "cant log", "can't log", "login", "password", "reset", "500")),
    ("general", ()),
)
URGENT_WORDS = ("urgent", "asap", "immediately", "charged twice", "double charged",
                "lost my", "locked out", "down", "outage", "legal", "cancel")
NEGATIVE_WORDS = ("angry", "unacceptable", "ridiculous", "terrible", "awful",
                  "frustrated", "disappointed", "scam", "worst", "still waiting",
                  "no response", "third time")

NGRAM = 4          # word n-gram width used for the support check
MIN_WORDS = 4      # shorter sentences (greetings) are shown but not scored
SUPPORT_RATIO = 0.5  # fraction of a sentence's n-grams that must be grounded


# --- pure ----------------------------------------------------------------

def words(text: str) -> list[str]:
    """Citation markers ([1]) are stripped so they can't dilute the score."""
    clean = re.sub(r"\[\d+\]", " ", text or "")
    return re.findall(r"[a-z0-9']+", clean.lower())


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


def ngrams(ws: list[str], n: int = NGRAM) -> list[tuple]:
    return [tuple(ws[i:i + n]) for i in range(max(0, len(ws) - n + 1))]


def categorize(text: str) -> str:
    low = (text or "").lower()
    for name, keys in CATEGORY_RULES:
        if any(k in low for k in keys):
            return name
    return "general"


def urgency(text: str) -> str:
    low = (text or "").lower()
    return "high" if any(k in low for k in URGENT_WORDS) else "normal"


def sentiment(text: str) -> str:
    low = (text or "").lower()
    return "negative" if any(k in low for k in NEGATIVE_WORDS) else "neutral"


def critic(draft: str, sources: list[str]) -> dict:
    """Every scored draft sentence is checked against the source chunks."""
    src = [ngrams(words(s)) for s in sources]
    src_sets = [set(g) for g in src]
    all_grams = set().union(*src_sets) if src_sets else set()

    rows, supported, scored = [], 0, 0
    for s in sentences(draft):
        ws = words(s)
        if len(ws) < MIN_WORDS:
            rows.append({"sentence": s, "supported": None, "matched": ""})
            continue
        grams = ngrams(ws)
        hits = sum(1 for g in grams if g in all_grams)
        ratio = hits / len(grams) if grams else 0.0
        good = ratio >= SUPPORT_RATIO
        scored += 1
        supported += int(good)
        best, best_ratio = "", 0.0
        for i, gs in enumerate(src_sets):
            r = sum(1 for g in grams if g in gs) / len(grams) if grams else 0.0
            if r > best_ratio:
                best, best_ratio = f"[{i + 1}]", r
        rows.append({"sentence": s, "supported": good,
                     "matched": best if good else ""})
    score = supported / scored if scored else 0.0
    return {"score": round(score, 4), "sentences": rows}


def quoted_answer(chunks: list[dict]) -> str:
    """Grounded template fallback: quote retrieved paragraphs verbatim + citation."""
    if not chunks:
        return ("I couldn't find anything in our documentation that covers this. "
                "A human will take over from here.")
    return "\n\n".join(f"{c['text'].strip()} [{i + 1}]" for i, c in enumerate(chunks))


def status_for(score: float, threshold: float, n_sources: int) -> str:
    if n_sources == 0 or score < threshold / 2:
        return "needs_human"
    if score < threshold:
        return "low_confidence"
    return "ready"


# --- IO ------------------------------------------------------------------

def draft_answer(question: str, chunks: list[dict]) -> tuple[str, str]:
    """BYOK draft; ai.generate never returns '' (it falls back to the quoted
    template), so this always yields a draft."""
    import ai

    draft = ai.generate("support_reply", {"question": question, "chunks": chunks})
    return draft, ("ai" if ai.configured() else "template")


def process(ticket_id: int) -> dict:
    with db.get() as con:
        t = con.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if t is None:
            return {"ok": False, "msg": "no such ticket"}
        chunks = kb.search(con, t["body"], limit=3)
        threshold = (float(db.get_setting(con, "min_confidence", "60") or 60)) / 100

    sources = [c["text"] for c in chunks]
    draft, used = draft_answer(t["body"], chunks)
    check = critic(draft, sources)

    # Self-correction: only when a key is set AND the draft is ungrounded.
    if used == "ai" and chunks and check["score"] < threshold:
        import ai

        retry = ai.generate("support_reply", {
            "question": t["body"], "chunks": chunks,
            "previous": draft,
            "feedback": "Sentences not supported by the sources: " + "; ".join(
                r["sentence"] for r in check["sentences"] if r["supported"] is False
            ),
        })
        retry_check = critic(retry, sources)
        if retry_check["score"] > check["score"]:
            draft, check = retry, retry_check

    status = status_for(check["score"], threshold, len(chunks))
    citations = [{"n": i + 1, "doc": c["doc"], "text": c["text"]}
                 for i, c in enumerate(chunks)]

    with db.get() as con:
        con.execute(
            "UPDATE tickets SET category=?, urgency=?, sentiment=?, status=?, "
            "draft=?, confidence=?, n_sources=?, citations=?, critic=? WHERE id=?",
            (categorize(t["body"]), urgency(t["body"]), sentiment(t["body"]), status,
             draft, check["score"], len(chunks),
             json.dumps(citations), json.dumps(check["sentences"]), ticket_id),
        )
    return {"ok": True, "ticket_id": ticket_id, "status": status,
            "confidence": check["score"], "draft_source": used}
