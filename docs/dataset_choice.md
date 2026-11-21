# Dataset for Danish (checked 2026-11-21)

The dataset was fixed by the group's registration on the class sheet: **NST Danish ASR Database
(16 kHz), reorganized version, Språkbanken sbr-55**. This file records what we checked about it
against the plan's requirements.

| Requirement | NST Danish (sbr-55) | Where checked |
|---|---|---|
| Human reference transcripts | yes: the manuscript line each speaker read (prompted read speech) | resource documentation (`dk-16khz_reorganized_02.pdf`) |
| Speaker IDs | one recording session (`pid`) per speaker; the separate `Speaker_ID` field is inconsistent (same value with different sex/age), so we use the session | metadata, our check in `scripts/01_download.py` / D4 |
| Speaker metadata | sex, age, dialect region (7 regions), region of youth | metadata JSON / CSV |
| License allows a public repo | yes, CC0 | resource page |
| Size | training part 751 sessions (~310 lines each, about half are sentences), test part 57 sessions; the class sheet quotes ≈390 h available | metadata files; class sheet |
| Audio | 16 kHz, 16-bit PCM WAV, two channels (close / distant microphone) split into separate files | documentation; measured on the downloaded files |

**What we use:** sentences of 77 dan0565 sessions, channel 1, ~20 h after cleaning: 1.5 h each
for dev and test (held-out speakers), the rest train. Less than the "25 h planned" on the class
sheet, because of a same-day deadline and a slow connection (`docs/decisions.md` D10).

**Points to keep in mind (reported in the README):**
- Read speech from manuscripts recorded in quiet rooms in 2000: much easier than conversational
  or broadcast Danish, so WERs here do not transfer to spontaneous speech.
- Speakers read from shared manuscripts; we make dev/test sentence-disjoint from train.
- Several public Danish ASR models were fine-tuned on NST's training part, which our dev/test
  speakers also come from; our B5 model was not (see `docs/language_support.md`).
