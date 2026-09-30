"""Tests never push to a real phone, even when run on the laptop where .env holds the ntfy topic."""
import os

os.environ["ANANTA_NTFY_TOPIC"] = ""
