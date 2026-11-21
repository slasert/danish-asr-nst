# Decisions log (Group AEK, Project 3 ASR)

Each decision has a date and a reason. Newest decisions at the bottom.

## D0 — Restart in Danish — 2026-11-21
- A first version of this project was built on Polish (VoxPopuli) on 2026-11-20. The class
  coordination sheet registers group AEK as **Danish (da)**, dataset "reorganized version
  (Språkbanken / National Library of Norway, sbr-55)", "25 h planned (≈390 h available)".
  The project was therefore redone from scratch in Danish on that dataset. Nothing from the
  Polish runs (data, models, numbers) is used here.

## D1 — Language: Danish (da) — 2026-11-21
- Registered for AEK on the class sheet (see D0).
- **Mother-tongue rule:** to be confirmed by every member in their `contributions/` file.
  The team is at a Turkish university; Turkish was excluded up front.
- **Other groups:** the class sheet lists every group's language and dataset; record here who
  confirmed that no other group uses Danish or NST, and when.
- Baseline coverage (`docs/language_support.md`): B5 and B7–B10 have Danish checkpoints;
  **B6 (HuBERT + CTC) has no Danish checkpoint** and is documented, not run.

## D2 — Dataset: NST Danish ASR Database (16 kHz), reorganized, Språkbanken sbr-55 — 2026-11-21
- Source: <https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-55/>, license **CC0**
  (public-domain dedication), so redistribution in a public GitHub repo is allowed.
- Manuscript-read Danish recorded by Nordisk Språkteknologi in 2000; one WAV file per manuscript
  line; per-speaker metadata: sex, age, **dialect region** (7 regions), region of youth.
- NST's own parts: training (dan0565, 751 sessions) and test (dan0611, 57 sessions). We use
  dan0565 only (see D4 for why not dan0611).
- We use **sentence** lines only (NST type codes containing `IS`); single words, spelled words,
  names and digit strings are left out, because they are not continuous speech.
- **Channel 1** (close-talk microphone). Channel 2 (distant microphone) is not used.

## D3 — Storage — 2026-11-21
- The selected raw WAV files (~5 GB) are not committed: they are byte-identical to files in a
  stable public CC0 archive, and `scripts/01_download.py` rebuilds `data/raw/audio/` from it
  (SHA-256 of every file in `data/raw/CHECKSUMS.sha256`). `data/raw/metadata.tsv` is committed.
- The cleaned audio (16-bit FLAC, lossless) is committed with plain git (each file well under
  100 MB), so every experiment can be re-run from the repository alone.

## D4 — Selection and splits — 2026-11-21
- Speaker = one NST recording session (`pid`). NST's `Speaker_ID` field is not usable: the same
  value is attached to sessions with different sex and age (checked in the metadata).
- Selection: 126 dan0565 sessions drawn with the seed (balanced over dialect region x sex); of
  these we keep the first 77 in archive order (D10), so the download stopped at about 63 % of
  the 27.5 GB archive. The archive order is unrelated to speaker, station, date or region (checked
  on the extraction order), so the 77 are still a random subset.
- **Changed during the work (connection):** the first plan took dev/test from NST's separate
  test part dan0611 (a 10.4 GB archive). The machine's internet connection turned out to be slow
  and metered (about 1-4 MB/s, frequent drops), so dev/test are instead held-out **speakers of
  the same 77 sessions**. They are still speaker-disjoint and sentence-disjoint from train. The
  cost: dev/test are not NST's official test speakers. Our B5 checkpoint (CoRal) was not trained
  on NST and the other pretrained cards do not name NST, so no baseline is known to have seen them.
- dev and test: ~1.5 h each, speakers dealt alternately per (sex, dialect) cell; train: all other speakers.
- Sentences are read from shared manuscripts: every training clip whose sentence also occurs in
  dev or test is removed from train (sentence-disjoint evaluation). Seed 1234 (`configs/seeds.yaml`).

## D5 — Reference transcript and normalization — 2026-11-21
- Reference = the NST manuscript line (what the speaker was asked to read). Orthographic
  reference keeps case and punctuation; normalized reference = `src/normalize.py` applied to it.
- Dictation lines with spoken punctuation commands (`\Komma`, `\Punktum` ...) are removed: the
  speaker says "komma", but whether a system should write the word or the comma is undefined.
- We cannot check automatically that the speaker read the line exactly; the manual audit
  (`scripts/05_audit.py`) measures this. We never correct references with a model.
- One normalizer for every system (Danish letters æ ø å kept, optional accents folded, numbers
  written out in Danish).

## D6 — B1 GMM-HMM implemented in Python, not Kaldi — 2026-11-21
- Kaldi needs Linux; on the training machine Docker's engine failed and WSL had no networking, so
  the classical recipe (MFCC+Δ+ΔΔ, CMVN, 3-state grapheme HMMs, diagonal GMMs, Viterbi training
  with mixture splitting, bigram LM, Viterbi decoding) is implemented in Python. Difference to a
  Kaldi tri1 system: no triphones, grapheme-level LM, no lexicon (hard for Danish spelling).

## D7 — Contribution: full fine-tuning of openai/whisper-small — 2026-11-21
- Largest multilingual Whisper that fits our 4 GB GPU for full fine-tuning (Adafactor, fp16,
  gradient checkpointing). Compared against B7 (same checkpoint, no training) with identical
  decoding, plus a paired bootstrap CI.

## D8 — Checkpoint selection for the neural baselines — 2026-11-21
- B2 CTC, B3a AED and B4 RNN-T: the epoch with the lowest dev WER under fast greedy decoding.
- B3b hybrid: the epoch with the lowest dev WER of its CTC head (greedy); greedy attention decoding
  is unreliable early in training. The final hybrid decode is attention beam search + CTC rescoring.

## D9 — Order of the pretrained runs — 2026-11-21
- Pretrained baselines are vanilla (nothing tuned on dev), so each was run on dev and then on test,
  and its download deleted afterwards (too little free disk for all checkpoints at once). Our own
  systems are decoded on test only after training and dev-based selection are finished.

## D10 — Same-day deadline: less data, fewer epochs — 2026-11-21
- The project had to be finished on 2026-11-21. At 17:35 the download had 77 complete sessions
  (~20 h of clean sentences); it was stopped there instead of waiting 1–2 more hours for the
  planned 25 h. dev and test are 1.5 h each, train is everything else (~15 h after the
  sentence-overlap filter).
- Training budgets were cut to fit the deadline: B2–B4 6 epochs (instead of 60, learning-rate
  warmup 250 steps instead of 1000, so it stays ~15 % of training), the
  Whisper fine-tuning one epoch (instead of up to 6). Selection is still on dev only. These are
  smaller budgets than the systems would need to converge; the README says so next to the results.
