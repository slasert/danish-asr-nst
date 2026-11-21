"""Split tests: speaker disjointness, dev/test mix, sentence separation, seed determinism."""
import importlib.util

import pandas as pd

from src.config import CLEANED, ROOT, SPLITS, seed
from src.normalize import normalize

spec = importlib.util.spec_from_file_location("mk", ROOT / "scripts" / "03_make_splits.py")
mk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mk)


def read(p):
    return pd.read_csv(p, sep="\t", keep_default_na=False, quoting=3, dtype=str)


PARTS = {s: read(SPLITS / f"{s}.tsv") for s in ("train", "dev", "test")}
CLEANED_META = read(CLEANED / "metadata.tsv")


def test_speakers_disjoint():
    s = {k: set(v.speaker) for k, v in PARTS.items()}
    assert not (s["train"] & s["dev"]) and not (s["train"] & s["test"]) and not (s["dev"] & s["test"])


def test_dev_and_test_cover_both_sexes_and_most_regions():
    for k in ("dev", "test"):
        assert set(PARTS[k].gender) == {"female", "male"}
        assert PARTS[k].dialect.nunique() >= 5


def test_no_dev_or_test_sentence_in_train():
    train = set(PARTS["train"].text.map(normalize))
    for k in ("dev", "test"):
        assert not PARTS[k].text.map(normalize).isin(train).any()


def test_every_clip_in_at_most_one_split():
    ids = pd.concat([v.utt_id for v in PARTS.values()])
    assert ids.is_unique and set(ids) <= set(CLEANED_META.utt_id)


def test_same_seed_same_split():
    meta = CLEANED_META.copy()
    meta["duration"] = meta.duration.astype(float)
    a, b = mk.make_splits(meta, seed()), mk.make_splits(meta, seed())
    assert a.equals(b)
    on_disk = {u: k for k, v in PARTS.items() for u in v.utt_id}
    assert dict(zip(meta.utt_id[a.notna()], a[a.notna()])) == on_disk


def test_split_sizes_match_plan():
    hours = {k: v.duration.astype(float).sum() / 3600 for k, v in PARTS.items()}
    assert hours["train"] >= 12.0
    for k in ("dev", "test"):
        assert 1.5 <= hours[k] <= 1.9
