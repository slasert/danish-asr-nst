"""Clean data/raw/ -> data/cleaned/ and log every removal or fix to data/cleaning_log.csv.

Checks (first failing removal check decides the reason; fixes are logged separately):
  CORRUPT_AUDIO        unreadable file, zero length, wrong sample rate, channels or sample format
  SILENCE_PROMPT       the manuscript line is NST's silence prompt "( ... tavshed under denne
                       indspilning ...)": the speaker was asked to stay silent, there is no text
  DICTATION_COMMANDS   dictation lines with spoken punctuation commands ("\\Komma", "\\Punktum",
                       "\\Bindestreg" ...). The speaker says "komma" aloud, but whether a system
                       should output the word or the comma is undefined, so the reference is
                       ambiguous for every system
  EMPTY_TRANSCRIPT     empty normalized transcript
  UNICODE_FIX          (fix) transcript was not NFC
  BAD_CHARSET          digits, markup (< > ( ) \\) or letters that are not Latin
  DURATION_OUTLIER     shorter than min or longer than max duration
  SILENCE              mostly silent frames, or the whole clip is near-silent
  CLIPPED              too many samples at full scale
  RATE_MISALIGN        characters per second far outside the corpus distribution
                       (a misread, truncated or wrongly paired recording)
  DUP_AUDIO            identical audio samples (keep one)
  DUP_UTT              same (speaker, normalized transcript) pair (keep one)

We cannot check by machine whether the speaker read the manuscript line exactly; the manual
audit (scripts/05_audit.py) measures how often they did not.
Format conversion is not cleaning: we write 16-bit FLAC, lossless from the 16-bit PCM WAV.
"""
from __future__ import annotations

import csv
import hashlib
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import CLEANED, DATA, RAW, ROOT  # noqa: E402
from src.normalize import normalize, orthographic  # noqa: E402

SR = 16000
LOG_COLUMNS = ["utt_id", "speaker", "issue", "action", "detail"]
SILENCE_PROMPT = "tavshed under denne indspilning"


def audio_stats(x: np.ndarray, cfg: dict) -> dict:
    frame = 400  # 25 ms
    n = len(x) // frame * frame
    fr = x[:n].reshape(-1, frame) if n else x.reshape(1, -1)
    e = 10 * np.log10((fr.astype(np.float64) ** 2).mean(1) + 1e-12)
    return {
        "peak_db": float(e.max()),
        "silence_frac": float((e < e.max() - cfg["silence_frame_db"]).mean()),
        "clipped_frac": float((np.abs(x) >= cfg["clip_level"]).mean()),
    }


def main():
    cfg = yaml.safe_load(open(ROOT / "configs" / "cleaning.yaml", encoding="utf-8"))
    meta = pd.read_csv(RAW / "metadata.tsv", sep="\t", keep_default_na=False, quoting=3, dtype=str)
    log: list[list[str]] = []
    keep: list[dict] = []

    def drop(r, issue, detail=""):
        log.append([r["utt_id"], r["speaker"], issue, "removed", detail])

    for r in meta.to_dict("records"):
        # --- audio readable? ---
        try:
            info = sf.info(RAW / r["file"])
            x, sr = sf.read(RAW / r["file"], dtype="int16", always_2d=True)
        except Exception as e:  # noqa: BLE001
            drop(r, "CORRUPT_AUDIO", f"unreadable: {e}")
            continue
        if sr != SR or x.shape[1] != 1 or len(x) == 0 or info.subtype != "PCM_16":
            drop(r, "CORRUPT_AUDIO", f"sr={sr} ch={x.shape[1]} n={len(x)} {info.subtype}")
            continue
        pcm = x[:, 0]
        xf = pcm.astype(np.float32) / 32768
        dur = len(pcm) / SR
        # --- transcript checks ---
        text = r["text"]
        if SILENCE_PROMPT in text:
            drop(r, "SILENCE_PROMPT", text[:80])
            continue
        if "\\" in text:
            drop(r, "DICTATION_COMMANDS", text[:120])
            continue
        if not normalize(text):
            drop(r, "EMPTY_TRANSCRIPT")
            continue
        if unicodedata.normalize("NFC", text) != text:
            text = unicodedata.normalize("NFC", text)
            log.append([r["utt_id"], r["speaker"], "UNICODE_FIX", "fixed", "NFC"])
        bad = sorted({c for c in text if c.isdigit() or c in "<>()[]\\" or (c.isalpha() and not
                      unicodedata.name(c, "").startswith("LATIN"))})
        if bad:
            drop(r, "BAD_CHARSET", "".join(bad) + " | " + text[:100])
            continue
        # --- audio checks ---
        if not (cfg["min_duration_s"] <= dur <= cfg["max_duration_s"]):
            drop(r, "DURATION_OUTLIER", f"{dur:.2f}s")
            continue
        st = audio_stats(xf, cfg)
        if st["silence_frac"] > cfg["max_silence_fraction"] or st["peak_db"] < cfg["min_peak_dbfs"]:
            drop(r, "SILENCE", f"silent_frac={st['silence_frac']:.2f} peak={st['peak_db']:.1f}dB")
            continue
        if st["clipped_frac"] > cfg["max_clipped_fraction"]:
            drop(r, "CLIPPED", f"clipped_frac={st['clipped_frac']:.4f}")
            continue
        r.update(text_orth=orthographic(text), text=normalize(text), duration=dur,
                 cps=len(normalize(text).replace(" ", "")) / dur,
                 audio_sha=hashlib.sha256(pcm.tobytes()).hexdigest())
        keep.append(r)

    # --- speaking-rate outliers (robust z over all clips that passed so far) ---
    cps = np.array([k["cps"] for k in keep])
    med = float(np.median(cps))
    sigma = 1.4826 * float(np.median(np.abs(cps - med)))
    survivors = []
    for k in keep:
        z = (k["cps"] - med) / sigma
        if abs(z) > cfg["rate_robust_z"]:
            drop(k, "RATE_MISALIGN", f"cps={k['cps']:.2f} z={z:.2f} median={med:.2f}")
        else:
            survivors.append(k)

    # --- duplicates: keep the longest copy, ties broken by utt_id ---
    def dedup(items, key, issue):
        items = sorted(items, key=lambda k: (-k["duration"], k["utt_id"]))
        seen, out = {}, []
        for k in items:
            kk = key(k)
            if kk in seen:
                drop(k, issue, f"duplicate of {seen[kk]}")
            else:
                seen[kk] = k["utt_id"]
                out.append(k)
        return out

    survivors = dedup(survivors, lambda k: k["audio_sha"], "DUP_AUDIO")
    survivors = dedup(survivors, lambda k: (k["speaker"], k["text"]), "DUP_UTT")
    survivors.sort(key=lambda k: k["utt_id"])

    # --- write cleaned set ---
    if CLEANED.exists():
        shutil.rmtree(CLEANED)
    (CLEANED / "audio").mkdir(parents=True)
    cols = ["utt_id", "file", "speaker", "gender", "dialect", "age", "type", "duration", "text",
            "text_orth"]
    rows = []
    for k in survivors:
        pcm = sf.read(RAW / k["file"], dtype="int16")[0]
        rel = f"audio/{k['utt_id']}.flac"
        sf.write(CLEANED / rel, pcm, SR, subtype="PCM_16", format="FLAC")
        rows.append([k["utt_id"], rel, k["speaker"], k["sex"], k["dialect"], k["age"], k["type"],
                     f"{k['duration']:.3f}", k["text"], k["text_orth"]])
    with open(CLEANED / "metadata.tsv", "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(cols) + "\n")
        for row in rows:
            f.write("\t".join(row) + "\n")

    log.sort(key=lambda x: (x[2], x[0]))
    with open(DATA / "cleaning_log.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(LOG_COLUMNS)
        w.writerows(log)
    removed = sum(1 for x in log if x[3] == "removed")
    print(f"raw={len(meta)} kept={len(rows)} removed={removed} "
          f"fixed={sum(1 for x in log if x[3] == 'fixed')} hours_kept="
          f"{sum(float(r[7]) for r in rows) / 3600:.2f} rate_median={med:.2f} rate_sigma={sigma:.2f}")


if __name__ == "__main__":
    main()
