"""Ananta API client — full implementation (packed)."""
from __future__ import annotations
import base64

from src.tools._ananta_api_payload import _B64

exec(compile(base64.b64decode(_B64).decode("utf-8"), "ananta_api.py", "exec"), globals())
