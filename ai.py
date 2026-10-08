"""The ONLY module that talks to an LLM endpoint (BUILD §3).

BYOK: key comes from the Settings page (SQLite `settings`) or env
(AI_BASE_URL / AI_API_KEY / AI_MODEL). Never hardcoded, never logged.

generate(kind, ctx) -> str   # never raises, never returns "" — with no key or
                             # any failure it returns a deterministic template
                             # built from grounded data, so the app works at $0.
"""
import os

import db

SETTING_KEYS = ("ai_base_url", "ai_api_key", "ai_model")
ENV_KEYS = ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL")
SHORT = ("base_url", "api_key", "model")
PROMPTS = {
    "support_reply": (
        "You are a customer support agent. Answer the customer's question using ONLY "
        "the numbered source paragraphs provided. Cite the paragraph number you used, "
        "like [1]. If the sources do not cover the question, reply exactly: "
        "'I couldn't find anything in our documentation that covers this.' "
        "Do not invent policies, prices, or timelines. Two or three sentences."
    ),
}


def config() -> dict:
    with db.get() as con:
        s = {k: db.get_setting(con, k) for k in SETTING_KEYS}
    cfg = {k: (s[sk] or os.getenv(e, ""))
           for k, sk, e in zip(SHORT, SETTING_KEYS, ENV_KEYS)}
    cfg["base_url"] = cfg["base_url"].rstrip("/")
    cfg["model"] = cfg["model"] or "gpt-4o-mini"
    return cfg


def configured() -> bool:
    c = config()
    return bool(c["base_url"] and c["api_key"])


def template(kind: str, ctx: dict) -> str:
    if kind == "support_reply":
        import pipeline

        return pipeline.quoted_answer(ctx.get("chunks") or [])
    return ""


def generate(kind: str, ctx: dict) -> str:
    """One OpenAI-compatible POST /chat/completions. Falls back to template()."""
    cfg = config()
    if not cfg["base_url"] or not cfg["api_key"]:
        return template(kind, ctx)

    chunks = ctx.get("chunks") or []
    src = "\n\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks)) or "(none)"
    user = f"Sources:\n{src}\n\nCustomer question: {ctx.get('question', '')}"
    if ctx.get("previous"):
        user += f"\n\nPrevious ungrounded draft:\n{ctx['previous']}\n\n{ctx.get('feedback', '')}"

    import httpx

    try:
        r = httpx.post(
            f"{cfg['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {cfg['api_key']}"},
            json={"model": cfg["model"], "temperature": 0.2,
                  "messages": [{"role": "system", "content": PROMPTS.get(kind, PROMPTS["support_reply"])},
                               {"role": "user", "content": user}]},
            timeout=60,
        )
        r.raise_for_status()
        text = (r.json()["choices"][0]["message"]["content"] or "").strip()
        return text or template(kind, ctx)
    except Exception:
        return template(kind, ctx)


def test_connection() -> dict:
    """One cheap call; returns {ok, msg}. Never echoes the key."""
    if not configured():
        return {"ok": False, "msg": "No base URL / API key set (env or Settings)"}
    out = generate("support_reply", {"question": "Do you ship to Canada?",
                                     "chunks": [{"text": "We ship to Canada in 5 days."}]})
    return {"ok": bool(out), "msg": (out[:120] or "empty response")}
