"""27 Nov 2026 (flag 230, the 23 Nov audit): the trials list's options line takes its count and rupees from the line's own book
(paper/sp1/book.json), not from a read model built before the 17:30 IST scoring."""
import json

from india import paths, trials

BOOK = {"updated": "2026-11-27T17:30:08+05:30", "sessions": 22, "by_index": {
    "NIFTY": {"trades": 4, "index_proxy_sum_bps": 59.82, "option_1lot_rs_realistic_fill": 3393.0, "scored_late": 0},
    "BANKNIFTY": {"trades": 19, "index_proxy_sum_bps": 893.67, "option_1lot_rs_realistic_fill": 103219.0, "scored_late": 1}}}
RM_WORDS = ("Fri 27 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 21 scored session(s): "
            "NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 18 scored trade(s), index +800 bp, "
            "one option lot Rs 43,431 with realistic fills")


def test_words_take_the_book_part_from_the_book():
    w = trials.sp1_words(RM_WORDS, BOOK)
    assert w.startswith("Fri 27 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 22 scored session(s), scored to Fri 27 Nov:")
    assert "BANKNIFTY: 19 scored trade(s) (1 scored late), index +894 bp, one option lot Rs 103,219 with realistic fills" in w
    assert "43,431" not in w and "21 scored" not in w


def test_the_list_and_the_book_agree(tmp_path, monkeypatch):
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    (tmp_path / "paper" / "sp1" / "book.json").write_text(json.dumps(BOOK))
    (tmp_path / "readmodel").mkdir()
    (tmp_path / "readmodel" / "latest.json").write_text(json.dumps({"data_through": "2026-11-26",
                                                                     "sp1": {"book": {"sessions": 21}, "words": RM_WORDS}}))
    man = tmp_path / "manifests"
    man.mkdir()
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(paths, "manifest_dir", lambda: man)
    monkeypatch.setattr(trials, "_sessions", lambda: [])
    out = trials.build()
    row = next(r for r in out["trials"] if r["name"] == "the options line")
    assert row["done"] == BOOK["sessions"]
    assert "Rs 103,219" in row["so_far"]
    assert json.loads((man / "trials.json").read_text())["trials"][-1]["done"] == 22
