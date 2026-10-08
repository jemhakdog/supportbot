"""Knowledge base: chunk FAQ text, index into FTS5, retrieve by keyword.

Pure: chunk_text, tokens, match_query (checks.py tests these).
IO: index_document, search.
"""
import re

import db

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "so", "to", "of",
    "in", "on", "at", "for", "with", "is", "are", "was", "were", "be", "been",
    "do", "does", "did", "have", "has", "had", "i", "we", "you", "my", "our",
    "your", "it", "this", "that", "there", "here", "can", "could", "would",
    "should", "will", "how", "what", "when", "where", "why", "who", "not",
    "no", "yes", "about", "from", "get", "got", "me", "as", "by", "just",
    # support-message noise: matching on these produces irrelevant quotes
    "offer", "please", "want", "need", "help", "know", "hello", "hi",
    "thanks", "regards", "sincerely", "best",
}


# --- pure ----------------------------------------------------------------

def chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    """Split on blank lines (paragraphs); hard-split oversized ones on a
    sentence boundary so one huge paste doesn't become one giant chunk."""
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text or ""):
        para = para.strip()
        while len(para) > max_chars:
            cut = para.rfind(". ", 0, max_chars)
            cut = cut + 1 if cut > 0 else max_chars
            piece = para[:cut].strip()
            if piece:
                out.append(piece)
            para = para[cut:].strip()
        if para:
            out.append(para)
    return out


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9']+", (text or "").lower())
            if len(w) > 2 and w not in STOPWORDS]


def match_query(question: str, limit: int = 12) -> str:
    """FTS5 MATCH string: quoted OR'd prefix terms (quoting keeps punctuation safe).
    '' when the question has no usable terms -> caller treats it as no match."""
    seen, terms = set(), []
    for t in tokens(question):
        if t not in seen:
            seen.add(t)
            terms.append(f'"{t}"*')   # prefix match: "refund"* hits "refunds"
        if len(terms) >= limit:
            break
    return " OR ".join(terms)


# --- IO ------------------------------------------------------------------

def index_document(con, title: str, text: str) -> dict:
    """Insert doc + chunks, mirroring every chunk into FTS5 by rowid."""
    chunks = chunk_text(text)
    if not chunks:
        return {"doc_id": None, "chunks": 0}
    cur = con.execute("INSERT INTO docs(title) VALUES(?)", (title.strip() or "untitled",))
    doc_id = cur.lastrowid
    for i, c in enumerate(chunks):
        cid = con.execute(
            "INSERT INTO chunks(doc_id, ordinal, text) VALUES(?,?,?)", (doc_id, i, c)
        ).lastrowid
        con.execute("INSERT INTO chunks_fts(rowid, text) VALUES(?,?)", (cid, c))
    return {"doc_id": doc_id, "chunks": len(chunks)}


def search(con, question: str, limit: int = 3) -> list[dict]:
    """Top-`limit` chunks by bm25. [] on no terms / no docs / FTS syntax error."""
    q = match_query(question)
    if not q:
        return []
    try:
        rows = con.execute(
            "SELECT c.id, c.text, d.title AS doc, bm25(chunks_fts) AS rank "
            "FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid "
            "JOIN docs d ON d.id = c.doc_id "
            "WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
            (q, limit),
        ).fetchall()
    except Exception:
        return []
    return [{"id": r["id"], "text": r["text"], "doc": r["doc"],
             "score": round(-r["rank"], 4)} for r in rows]
