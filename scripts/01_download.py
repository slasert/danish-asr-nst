"""Build data/raw/ from the NST Danish ASR Database (16 kHz, reorganized), Språkbanken sbr-55.

Source: https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-55/ (CC0 1.0).
NST recorded manuscript-read Danish in 2000. We use its training part (dan0565, 751 sessions;
one session = one speaker reading ~310 manuscript lines; each line is one WAV file).

What we take (only manuscript lines that are sentences, i.e. NST type codes containing "IS";
single words, spelled words, names and digit strings are left out):
  1. DRAWN_SESSIONS sessions, drawn with the global seed, round-robin over the 7 dialect regions
     x 2 sexes, so every cell is represented;
  2. of these, the first KEEP_SESSIONS in the order in which they are stored in the archive.
     The archive order is unrelated to speaker, region or date (checked), so this is still a
     random subset; it lets the download stop early (the user's connection is slow and metered):
     about 63 % of the 27.5 GB archive was read (77 sessions, a same-day deadline).
train, dev and test are all made from these sessions, split by speaker in 03_make_splits.py.
Audio: channel 1 (close-talk microphone), 16 kHz, 16-bit PCM WAV. Files are written with their
bytes unchanged. The archive is streamed: only the selected files ever touch the disk.
data/raw/sessions.txt lists the kept sessions in archive order; if it is complete, nothing is
downloaded again.

    python scripts/01_download.py --cache /path/to/cache
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import sys
import tarfile
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import RAW, seed  # noqa: E402
from src.net import ResumingStream  # noqa: E402

BASE = "https://www.nb.no/sbfil/talegjenkjenning/16kHz_2020/dk_2020/"
TRAIN_META = "ADB_OD_DAN_0565.tar.gz"     # one JSON per dan0565 session
TRAIN_AUDIO = "lydfiler_16_1.tar.gz"      # channel 1 of dan0565
DRAWN_SESSIONS = 126
KEEP_SESSIONS = 77
COLUMNS = ["utt_id", "part", "file", "speaker", "sex", "age", "dialect", "region_of_youth",
           "type", "text", "sha256"]


def fetch(cache: Path, name: str) -> Path:
    p = cache / name
    if not p.exists():
        print("downloading", BASE + name)
        urllib.request.urlretrieve(BASE + name, p)
    return p


def is_sentence(t: str) -> bool:
    return "IS" in t


def train_rows(cache: Path) -> list[dict]:
    sessions = []
    with tarfile.open(fetch(cache, TRAIN_META)) as tf:
        for m in tf:
            if m.isfile() and m.name.endswith(".json"):
                sessions.append(json.load(tf.extractfile(m)))
    ok = [s for s in sessions if s["info"].get("Sex") in ("Male", "Female")
          and s["system"].get("Frequency") == "16000" and s["info"].get("Region_of_Dialect")]
    cells = {}
    for s in sorted(ok, key=lambda s: s["pid"]):
        cells.setdefault((s["info"]["Region_of_Dialect"], s["info"]["Sex"]), []).append(s)
    rng = random.Random(seed())
    for k in sorted(cells):
        rng.shuffle(cells[k])
    chosen = []
    while len(chosen) < DRAWN_SESSIONS and any(cells.values()):
        for k in sorted(cells):
            if cells[k] and len(chosen) < DRAWN_SESSIONS:
                chosen.append(cells[k].pop())
    rows = []
    for s in chosen:
        i = s["info"]
        for r in s["val_recordings"]:
            if is_sentence(r["type"]):
                stem = f"{s['pid']}_{Path(r['file']).stem.lower()}-1"
                rows.append(dict(utt_id=stem, part="dan0565", member=f"dk/{s['pid']}/{stem}.wav",
                                 speaker=s["pid"], sex=i["Sex"].lower(), age=i.get("Age", ""),
                                 dialect=i["Region_of_Dialect"], region_of_youth=i.get("Region_of_Youth", ""),
                                 type=r["type"], text=r["text"]))
    print(f"drawn: {len(chosen)} of {len(ok)} usable dan0565 sessions, {len(rows)} sentence lines")
    return rows


def stream_extract(url: str, wanted: dict[str, Path], sessions: set[str], keep: int) -> list[str]:
    """Read the remote tar.gz sequentially and write the wanted members. A session's files are
    stored together, so a session is finished when the archive moves on to another folder.
    Stops after `keep` of our sessions are finished; returns them in archive order."""
    done, current = [], None
    raw = io.BufferedReader(ResumingStream(url), buffer_size=1 << 20)
    with tarfile.open(fileobj=raw, mode="r|gz") as tf:
        for m in tf:
            folder = m.name.split("/")[1] if m.name.count("/") >= 2 else None
            if folder != current:
                if current in sessions:
                    done.append(current)
                    print(f"  session {len(done)}/{keep} done: {current}", flush=True)
                    if len(done) == keep:
                        break
                current = folder
            if m.name in wanted and not wanted[m.name].exists():
                wanted[m.name].write_bytes(tf.extractfile(m).read())
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, help="folder for the small metadata downloads")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    audio = RAW / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    rows = train_rows(cache)
    order = RAW / "sessions.txt"
    kept = order.read_text(encoding="utf-8").split() if order.exists() else []
    if len(kept) < KEEP_SESSIONS:
        wanted = {r["member"]: audio / f"{r['utt_id']}.wav" for r in rows}
        print(f"streaming {TRAIN_AUDIO} until {KEEP_SESSIONS} of the drawn sessions are complete")
        kept = stream_extract(BASE + TRAIN_AUDIO, wanted, {r["speaker"] for r in rows}, KEEP_SESSIONS)
        order.write_text("\n".join(kept) + "\n", encoding="utf-8", newline="\n")
    rows = [r for r in rows if r["speaker"] in set(kept)]

    out = []
    for r in rows:
        p = audio / f"{r['utt_id']}.wav"
        if p.exists():  # lines that NST never recorded have no audio file; they are dropped here
            out.append([r["utt_id"], r["part"], f"audio/{p.name}", r["speaker"], r["sex"], r["age"],
                        r["dialect"], r["region_of_youth"], r["type"],
                        " ".join(r["text"].split()), hashlib.sha256(p.read_bytes()).hexdigest()])
    print(f"{len(rows) - len(out)} selected lines have no audio file in the archive")
    out.sort(key=lambda x: x[0])
    pd.DataFrame(out, columns=COLUMNS).to_csv(RAW / "metadata.tsv", sep="\t", index=False,
                                              quoting=3, lineterminator="\n")
    with open(RAW / "CHECKSUMS.sha256", "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(f"{r[-1]}  {r[2]}\n")
    print(f"wrote {len(out)} clips to {audio}")


if __name__ == "__main__":
    main()
