"""Ananta Canada: a separate research lab for TSX stocks (Madhav, Oct 14 2026).

Isolation rules (non-negotiable, enforced by tests/test_canada_isolation.py):
  - Nothing in jarvis/ or src/ imports this package, and this package imports nothing from them.
  - Its data lives outside every crypto folder (default ~/ananta_data/canada), never in docs/, so the
    agent's knowledge reader cannot see it.
  - No Canadian data may wake the agent, trigger a trade or influence a decision.
  - Every finding is RESEARCH until independently validated; the 2024+ holdout stays sealed until all
    five reviews have verdicts and Madhav approves opening it.
Phase C0 (planning and pre-registration) only: no research data has been downloaded.
"""
VERSION = "canada.c0"
