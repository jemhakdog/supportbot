"""One background worker thread + queue (BUILD §2). Triage runs here so
POST /tickets returns instantly and the page polls /tickets/<id>.json."""
import queue
import threading

_q: "queue.Queue[int]" = queue.Queue()


def _loop() -> None:
    while True:
        ticket_id = _q.get()
        try:
            import pipeline

            print(f"[supportbot] triage: {pipeline.process(ticket_id)}")
        except Exception as e:  # never let the thread die
            print(f"[supportbot] triage error on ticket {ticket_id}: {e}")
            try:
                import db

                with db.get() as con:
                    con.execute("UPDATE tickets SET status='needs_human' WHERE id=?",
                                (ticket_id,))
            except Exception:
                pass
        finally:
            _q.task_done()


def start_worker() -> threading.Thread:
    t = threading.Thread(target=_loop, daemon=True, name="supportbot-worker")
    t.start()
    return t


def enqueue(ticket_id: int) -> None:
    _q.put(ticket_id)
