# Frozen registrations

Empty until Madhav approves the C0 pre-registration document. At approval, each review's registration is
copied here verbatim as CA1.md ... CA5.md by `canada.registry.freeze()`, which records its SHA-256 hash in
`../registry/canada_status.json`. `canada.registry.verify()` (and the test suite) fail if a frozen file
changes. A changed criterion is never an edit: it is a new registration, approved separately, and it can
never use the 2024+ holdout.
