"""12 Nov 2026, the keen outside audit (G-58): each guest's practice book was a file named after the guest's email, and the nightly backup
and its weekly copy to the cloud carried that name. The name is now a fingerprint of the same key; the books (and archived copies) still
named after an email are renamed once, before any is opened. No real email appears here: the addresses are made up."""
import inspect
import re

from jarvis.service import app as A


def test_a_guests_book_is_named_by_a_fingerprint_not_the_email():
    n = A._sandbox_name("Jane.Doe@Example.com")
    assert re.fullmatch(r"g[0-9a-f]{16}", n)
    assert "jane" not in n and "example" not in n and "doe" not in n
    assert n == A._sandbox_name("jane.doe@example.com")                       # the same guest keeps the same book
    assert n != A._sandbox_name("john@example.com")
    assert n == A._fingerprint(A._legacy_sandbox_name("jane.doe@example.com"))   # so an old file can be renamed from its name alone


def test_books_journals_and_archives_named_after_an_email_are_renamed_once(tmp_path):
    legacy = A._legacy_sandbox_name("jane.doe@example.com")
    (tmp_path / f"jarvis_guest_{legacy}.sqlite").write_text("book")
    (tmp_path / f"jarvis_guest_{legacy}.sqlite-wal").write_text("wal")
    (tmp_path / "guest_archive").mkdir()
    (tmp_path / "guest_archive" / f"jarvis_guest_{legacy}.1794000000.sqlite").write_text("old book")
    (tmp_path / "jarvis.sqlite").write_text("owner")
    (tmp_path / "jarvis_guest_g0123456789abcdef.sqlite").write_text("already a fingerprint")
    assert A.rename_legacy_guest_files(tmp_path) == 3
    new = A._sandbox_name("jane.doe@example.com")
    assert (tmp_path / f"jarvis_guest_{new}.sqlite").read_text() == "book"
    assert (tmp_path / f"jarvis_guest_{new}.sqlite-wal").read_text() == "wal"
    assert (tmp_path / "guest_archive" / f"jarvis_guest_{new}.1794000000.sqlite").read_text() == "old book"
    names = " ".join(p.name for p in tmp_path.rglob("*"))
    assert "jane" not in names and "example" not in names
    assert (tmp_path / "jarvis.sqlite").read_text() == "owner"
    assert (tmp_path / "jarvis_guest_g0123456789abcdef.sqlite").read_text() == "already a fingerprint"
    assert A.rename_legacy_guest_files(tmp_path) == 0                         # a second pass finds nothing


def test_a_book_is_never_renamed_over_one_that_has_the_new_name(tmp_path):
    legacy = A._legacy_sandbox_name("jane.doe@example.com")
    new = A._fingerprint(legacy)
    (tmp_path / f"jarvis_guest_{legacy}.sqlite").write_text("older")
    (tmp_path / f"jarvis_guest_{new}.sqlite").write_text("newer")
    assert A.rename_legacy_guest_files(tmp_path) == 0
    assert (tmp_path / f"jarvis_guest_{new}.sqlite").read_text() == "newer"


def test_every_way_to_a_guests_book_goes_through_the_fingerprint_and_the_rename():
    sb, ar = inspect.getsource(A._sandbox), inspect.getsource(A._archive_sandbox)
    assert "_sandbox_name(" in sb and "_rename_guest_files_once(" in sb
    assert "_sandbox_name(" in ar and "_rename_guest_files_once(" in ar
    src = inspect.getsource(A)
    assert len(re.findall(r'f"jarvis_guest_\{(\w+)\}', src)) == len(re.findall(r'f"jarvis_guest_\{name\}', src)) >= 3
