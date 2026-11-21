"""Speaker-disjoint train/dev/test split of data/cleaned/.

- The unit of assignment is the speaker (= one NST recording session, see README): all clips of
  a speaker go to one split.
- dev and test: the speakers are shuffled with the seed inside each (sex, dialect) cell; the
  cells are visited in turn, and each visit deals one speaker alternately to dev and to test,
  until both have EVAL_HOURS. So both get a similar mix of sexes and dialect regions.
- train: all remaining speakers (after the sentence-overlap removal below).
- Sentence overlap: NST speakers read from shared manuscripts. A train clip whose normalized
  sentence also occurs in dev or test is dropped from train (counted in split_stats.md), so no
  test sentence was seen in training.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import CLEANED, SPLITS, seed  # noqa: E402
from src.normalize import normalize  # noqa: E402

TRAIN_HOURS = float("inf")  # all remaining speakers (time limit: see docs/decisions.md D10)
EVAL_HOURS = 1.5  # each of dev and test


def speakers(meta: pd.DataFrame) -> pd.DataFrame:
    return meta.groupby("speaker").agg(hours=("duration", lambda d: d.sum() / 3600),
                                       gender=("gender", "first"), dialect=("dialect", "first")).reset_index()


def cells(spk: pd.DataFrame, rng: random.Random) -> dict:
    out = {k: list(g.sort_values("speaker").speaker) for k, g in spk.groupby(["gender", "dialect"])}
    for k in sorted(out):
        rng.shuffle(out[k])
    return out


def assign_eval(meta: pd.DataFrame, rng: random.Random) -> dict[str, str]:
    spk = speakers(meta)
    hours = dict(zip(spk.speaker, spk.hours))
    c = cells(spk, rng)
    out, filled, turn = {}, {"dev": 0.0, "test": 0.0}, 0
    while min(filled.values()) < EVAL_HOURS and any(c.values()):
        for k in sorted(c):
            split = ("dev", "test")[turn % 2]
            if filled[split] >= EVAL_HOURS:  # one split is full: the other takes the rest
                split = "test" if split == "dev" else "dev"
            if c[k] and filled[split] < EVAL_HOURS:
                sp = c[k].pop()
                out[sp] = split
                filled[split] += hours[sp]
                turn += 1
    return out


def assign_train(meta: pd.DataFrame, rng: random.Random) -> dict[str, str]:
    spk = speakers(meta)
    hours = dict(zip(spk.speaker, spk.hours))
    c = cells(spk, rng)
    out, filled = {}, 0.0
    while filled < TRAIN_HOURS and any(c.values()):
        for k in sorted(c):
            if c[k] and filled < TRAIN_HOURS:
                sp = c[k].pop()
                out[sp] = "train"
                filled += hours[sp]
    return out


def make_splits(meta: pd.DataFrame, s: int) -> pd.Series:
    """Split name per clip ("train", "dev", "test" or NaN = not used)."""
    rng = random.Random(s)
    split = meta["speaker"].map(assign_eval(meta, rng))
    eval_sents = set(meta[split.notna()].text.map(normalize))
    overlap = split.isna() & meta.text.map(normalize).isin(eval_sents)
    usable = meta[~overlap & split.isna()]
    split.loc[usable.index] = usable["speaker"].map(assign_train(usable, rng))
    return split


def main():
    meta = pd.read_csv(CLEANED / "metadata.tsv", sep="\t", keep_default_na=False, quoting=3,
                       dtype={"speaker": str})
    meta["duration"] = meta["duration"].astype(float)
    meta["split"] = make_splits(meta, seed())
    SPLITS.mkdir(parents=True, exist_ok=True)
    cols = ["utt_id", "path", "speaker", "gender", "dialect", "age", "duration", "text", "text_orth"]
    meta["path"] = "data/cleaned/" + meta["file"]
    for split in ("train", "dev", "test"):
        part = meta[meta.split == split].sort_values("utt_id")
        part[cols].to_csv(SPLITS / f"{split}.tsv", sep="\t", index=False, quoting=3,
                          lineterminator="\n")
        print(f"{split}: {len(part)} utts, {part.speaker.nunique()} speakers, "
              f"{part.duration.sum() / 3600:.2f} h")


if __name__ == "__main__":
    main()
