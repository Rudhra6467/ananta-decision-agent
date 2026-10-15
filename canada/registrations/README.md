# Frozen registrations

Empty until Madhav approves the C0 pre-registration document. At approval, `canada.registry.freeze_bundle()`
writes CA1.md ... CA5.md and the whole C0 document (C0_document.md) here verbatim, then hashes them together
with the rule code (`canada/validation.py`, `canada/costs.py`, `tests/test_canada_isolation.py`) as one
bundle recorded in `../registry/canada_status.json`. `canada.registry.verify()` names any file that changed.
A changed criterion, common rule or threshold is never an edit: it is a new registration, approved
separately, and it can never use the 2024+ holdout.
