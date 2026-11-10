# The backlog moved (10 Nov 2026)

This file was "the single list of remaining work" and was last kept on 4 Oct 2026. A list kept by hand goes stale.

**What is open now is in one place: the open list** (`jarvis/service/openlist.py`).

- Print it on the Mac: `python scripts/open_list.py` (in the service's environment), or GET `/v3/open`.
- Ask Ananta: "what's open", "what's waiting for my yes", "is X done".
- Four kinds: needs your yes, work to do, waiting for a date or for evidence, parked on purpose.
- A fix closes its item: name it in the change-book line's `closes` (stored numbers), or `python scripts/open_list.py --close <num> "what closed it"`.
- A dated note never holds its own open list. It says what was done and names the items it opened or closed.

The dated plan after the crypto lock is still `docs/knowledge/due_list.json`; the open list reads it live.
