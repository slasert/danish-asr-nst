# Danish Speech Recognition on NST — Group AEK (COE025 NLP, Project 3)

Automatic speech recognition for **Danish** on manuscript-read speech from the **NST Danish ASR
Database** (Språkbanken sbr-55), with speakers from all seven Danish dialect regions of the
corpus. We select and clean the data, split it by speaker, benchmark the course baselines under
one scorer, and fine-tune `openai/whisper-small` as our contribution.

**Every number in this README is generated** by `scripts/make_tables.py` from
`results/metrics/*.json` (written by `scripts/score.py` and `scripts/bootstrap.py`) or from
the data logs. Blocks between `<!-- BEGIN:… -->` and `<!-- END:… -->` are overwritten by that
script; `python scripts/make_tables.py --check` fails if they are out of date.

## 1. Group

| Member | GitHub | Contribution file |
|---|---|---|
| see `contributions/` | each member commits from their own account | `contributions/<NAME>_<STUDENT_ID>_<GITHUB_USERNAME>.md` |

## 2. Task and language

- **Language: Danish (da)**, as registered for group AEK on the class coordination sheet
  (`docs/decisions.md`, D0–D1).
- **Dialects:** every NST speaker has a dialect region (Storkøbenhavn, Fyn, Vest- og Sydsjælland,
  Vestjylland, Østjylland, Nordjylland, Sønderjylland). All seven are in train, dev and test,
  and we report test WER per region (Section 9).
- Why Danish is hard for ASR: spelling is far from pronunciation (silent letters, soft *d*,
  reduced endings, stød), so the same sounds map to many spellings; definite and plural forms are
  suffixes (*hus / huset / husene*), so one wrong ending is a whole word error for WER.
- **Not a member's mother tongue; not used by another group:** each member confirms this in
  their `contributions/` file; coordination with the other groups is logged in `docs/decisions.md`.

## 3. Dataset

| | |
|---|---|
| Source | **NST Danish ASR Database (16 kHz) – reorganized**, Språkbanken / National Library of Norway, [sbr-55](https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-55/) |
| License | **CC0** (public-domain dedication), see `DATA_LICENSE.md` |
| Content | Danish read from manuscripts, recorded by Nordisk Språkteknologi in 2000; one WAV file per manuscript line; we use NST's training part dan0565 (751 sessions) |
| Part used | **sentence** lines only (NST type codes containing `IS`), **channel 1** (close-talk microphone), 16 kHz 16-bit PCM |
| Selection | `scripts/01_download.py`: 126 sessions drawn with seed 1234, cycling over the 7 dialect regions × 2 sexes; of these, the first 77 in archive order (a random subset: the archive order is unrelated to speaker or region), so the download stopped after ~63 % of the 27.5 GB archive (slow, metered connection and a same-day deadline; `docs/decisions.md` D4, D10) |
| Transcripts | the manuscript line the speaker was asked to read (human-written); cased and punctuated |
| Speaker info | one recording session per speaker; sex, age, dialect region, region of youth |
| Size | ~20 h of clean sentences from 77 speakers: dev and test 1.5 h each, train = the rest after the sentence-overlap filter (exact hours in Section 5). The class sheet says "25 h planned"; we used less because of the deadline (D10) |

The raw WAV files are **not** committed (byte-identical to the public CC0 archive):
`python scripts/01_download.py --cache <folder>` rebuilds `data/raw/audio/` by streaming the
archive and keeping only the selected files (`data/raw/sessions.txt` lists the 77 sessions); `data/raw/CHECKSUMS.sha256` holds the SHA-256 of
every file and `data/raw/metadata.tsv` all metadata. The **cleaned** audio (FLAC) is committed, so
every experiment runs from the repository alone.

## 4. Cleaning

`python scripts/02_clean.py` turns `data/raw/` into `data/cleaned/` and logs every removal and
fix to `data/cleaning_log.csv` (`utt_id, speaker, issue, action, detail`). Thresholds live in
`configs/cleaning.yaml`. The script is deterministic (tested). Writing 16-bit FLAC from 16-bit
WAV is lossless and is not counted as cleaning.

What we found and did:

| Check | What it catches in this data | Action |
|---|---|---|
| `DICTATION_COMMANDS` | NST's dictation manuscripts contain spoken punctuation commands (`…vendes,\Komma men…\Punktum`): the speaker says "komma" and "punktum" aloud. Whether a system should write the word or the comma is undefined, so the reference is ambiguous for every system. | remove |
| `SILENCE_PROMPT` | the manuscript line "( … tavshed under denne indspilning … )": the speaker was asked to stay silent, so there is no text to recognize | remove |
| `SILENCE` | more than half of the 25 ms frames are 40 dB below the clip's loudest frame (all flagged clips have normal loudness: long pauses before or after reading, or a partly missing reading) | remove |
| `RATE_MISALIGN` | characters per second more than 3.5 robust standard deviations (1.4826·MAD) from the median, e.g. 22.5 or 2.9 characters/s against a median of 11.1: the recording does not match its manuscript line | remove |
| `DURATION_OUTLIER` | shorter than 1 s (a cut-off recording) or longer than 30 s | remove |
| `CORRUPT_AUDIO`, `EMPTY_TRANSCRIPT`, `BAD_CHARSET`, `CLIPPED`, `DUP_AUDIO`, `DUP_UTT`, `UNICODE_FIX` | checked; nothing in this data triggered them (all files 16 kHz mono 16-bit PCM, NFC text, no digits or markup left after the rules above) | — |

NST lines that were never recorded have no audio file in the archive; `01_download.py` drops
them before cleaning (167 of the selected lines).

Summary of `data/cleaning_log.csv`:

<!-- BEGIN:cleaning -->
| Reason code | Action | Clips |
|---|---|---|
| `DICTATION_COMMANDS` | removed | 684 |
| `SILENCE` | removed | 177 |
| `SILENCE_PROMPT` | removed | 77 |
| `RATE_MISALIGN` | removed | 8 |
| `DURATION_OUTLIER` | removed | 1 |
| **total removed** | | **947** of 13077 |
| **kept** | | **12130** clips, 20.42 h |
<!-- END:cleaning -->

<!-- BEGIN:audit -->
**Manual audit:** not done yet. `scripts/05_audit.py sample` drew 100 random cleaned clips (`data/audit/audit_sample.tsv`); a team member listens to them in `data/audit/listen.html`, saves `data/audit/audit_results.csv` and runs `scripts/05_audit.py report`.
<!-- END:audit -->

## 5. Splits

`scripts/03_make_splits.py` assigns **whole speakers** (= recording sessions; NST's own
`Speaker_ID` field is inconsistent, see `docs/decisions.md` D4) to the splits:

- **dev / test** = held-out speakers: shuffled with the seed inside each (sex, dialect) cell,
  the cells visited in turn, one speaker per visit dealt alternately to dev and to test until
  each has 1.5 h, so both have a similar mix of sexes and regions;
- **train** = all remaining speakers;
- **sentence-disjoint:** NST speakers read from shared manuscripts, so a training clip whose
  sentence also occurs in dev or test is removed from train. No dev/test sentence is in train.

`scripts/04_split_stats.py` asserts speaker disjointness and reports hours per dialect region.

<!-- BEGIN:split_stats -->
Generated by `scripts/04_split_stats.py`. Speakers are pairwise disjoint (asserted).

| Split | Speakers | Utterances | Hours | Female hours share |
|---|---|---|---|---|
| train | 64 | 9061 | 14.76 | 45.8% |
| dev | 6 | 933 | 1.58 | 67.5% |
| test | 7 | 975 | 1.66 | 34.0% |
| **total** | 77 | 10969 | 17.99 | |

**dev sentences found word-for-word in train (after normalization):** 0 of 933 (0.00%)

**test sentences found word-for-word in train (after normalization):** 0 of 975 (0.00%)

**Hours per dialect region** (NST `Region_of_Dialect` of the speaker):

| Dialect region | train | dev | test |
|---|---|---|---|
| Fyn | 1.97 | 0.30 | 0.29 |
| Nordjylland | 2.37 | 0.28 | 0.31 |
| Storkøbenhavn | 1.66 | 0.29 | 0.24 |
| Sønderjylland | 3.03 | 0.23 | 0.25 |
| Vest- og Sydsjælland | 2.20 | 0.24 | 0.25 |
| Vestjylland | 1.70 | 0.00 | 0.31 |
| Østjylland | 1.83 | 0.24 | 0.00 |

Cleaned clips not used in any split (train-speaker clips whose sentence occurs in dev/test): 1161
<!-- END:split_stats -->

## 6. Metrics and normalization

Following the Hugging Face Audio Course, chapter 5 "Evaluation"
(<https://huggingface.co/learn/audio-course/en/chapter5/evaluation>):

- **WER** (word error rate, (S + D + I) / N over words) is the standard ASR metric and measures
  what a reader of the transcript experiences: a word is right or wrong. It is our **primary
  metric**. Its weakness for Danish: one wrong suffix (*huset* vs. *husene*) or a spelling
  variant counts as a full word error.
- **CER** (character error rate) gives partial credit for nearly-right words, which matters for
  Danish, where many errors are a single ending or a spelling variant. Reported for every system.
- **Corpus-level pooling:** WER = Σ(S+D+I) / ΣN over the whole split (`src/eval/metrics.py`); we
  never average per-clip WERs (tested).
- **Normalized vs. orthographic** (the course's distinction): *normalized* scores compare
  normalized hypothesis and reference (our primary numbers); *orthographic* scores keep casing and
  punctuation of the manuscript line, which shows how usable the raw output is. Our own CTC /
  transducer models are trained on lowercase text, so their orthographic WER is high by construction.
- **Normalization policy** (`src/normalize.py`, one function for every system): NFC → lowercase
  → digits written out as Danish cardinals with `num2words` (the references contain no digits,
  so this only stops systems from being punished for writing "21") → letters with accents that
  are not part of the Danish alphabet reduced to the base letter (æ ø å kept; *idé → ide*,
  *én → en*, because these accents are optional in Danish spelling) → apostrophes deleted →
  hyphens, dashes and all other punctuation become spaces → whitespace collapsed. We do not use
  Whisper's `EnglishTextNormalizer`, which applies English spelling rules.
- **Secondary:** S/D/I counts, MER and WIL are stored in every metrics JSON; RTFx (audio seconds
  / compute seconds, model loading excluded) with the hardware named.
- **Paired bootstrap** (`scripts/bootstrap.py`): 2,000 resamples of test utterances, the same
  draw for both systems, re-pooled WER/CER; we report the 95 % percentile interval of the difference.

## 7. Baselines

All systems are scored by `scripts/score.py` on the same test clips with the same references and
normalizer. Hardware: NVIDIA GeForce RTX 3050 Laptop GPU (4 GB), 7.8 GB RAM, Windows 11.

### Table A — pretrained baselines (no training by us)

<!-- BEGIN:table_a -->
| System | Family | Exact checkpoint @ revision | Language setting | Decoding | Dev WER | Test WER (norm) | Test CER (norm) | Test WER (orth) | Test CER (orth) | RTFx |
|---|---|---|---|---|---|---|---|---|---|---|
| `wav2vec2_roest_315m_da` | B5 SSL + CTC | [`CoRal-project/roest-v3-wav2vec2-315m`](https://huggingface.co/CoRal-project/roest-v3-wav2vec2-315m/tree/beb3e790246d6b9dec1df596b0b21d5c42f4d99c) @ `beb3e79024` | da (model is da-only) | greedy CTC (argmax), no language model | 10.93 | **14.00** | 3.96 | 32.08 | 7.94 | 118.85 |
| `whisper_small` | B7 pretrained AED | [`openai/whisper-small`](https://huggingface.co/openai/whisper-small/tree/973afd24965f72e36ca33b3055d56a652f456b4d) @ `973afd2496` | language='danish', task='transcribe' | greedy (num_beams=1), no timestamps | 24.46 | **28.01** | 10.16 | 31.11 | 11.48 | 29.76 |
| `canary_1b_v2` | B8 pretrained AED | [`nvidia/canary-1b-v2`](https://huggingface.co/nvidia/canary-1b-v2/tree/d455706339a6b32e1aa40f82c713a482a0c938e2) @ `d455706339` | source_lang='da', target_lang='da' | model-card default (beam search as configured in the .nemo, pnc=yes); timestamps model not loaded (restore_timestamps_model=False) | 7.70 | **9.95** | 3.61 | 12.31 | 4.66 | 33.71 |
| `parakeet_tdt_0.6b_v3` | B9 pretrained transducer | [`nvidia/parakeet-tdt-0.6b-v3`](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3/tree/541d1f99c6b0c3cd0b11a95167540bb8edefd82b) @ `541d1f99c6` | no language argument: the model detects the language itself (see model card) | model-card default (greedy TDT) | 12.15 | **15.12** | 5.15 | 17.51 | 6.14 | 129.0 |
| `qwen3_asr_0.6b` | B10 pretrained audio-LLM ASR | [`Qwen/Qwen3-ASR-0.6B`](https://huggingface.co/Qwen/Qwen3-ASR-0.6B/tree/5eb144179a02acc5e5ba31e748d22b0cf3e303b0) @ `5eb144179a` | language='Danish' | model-card default (transformers backend, greedy) | 27.49 | **31.13** | 12.30 | 33.58 | 12.80 | 14.08 |
<!-- END:table_a -->

Notes: B5 is the CoRal project's Danish wav2vec 2.0 model (XLS-R 300M + CTC), chosen because its
card names only CoRal-v3 as training data, not NST (`docs/language_support.md`); its repository
also ships a 3-gram LM, which we do not use (vanilla greedy CTC). Whisper is multilingual
`openai/whisper-small` (not `.en`). Parakeet is **v3**; it has no language argument (it identifies
the language itself, per its model card). Qwen3-ASR uses the 0.6B variant: the 1.7B model does
not fit in 4 GB in bf16. Canary's `.nemo` file also contains a separate 2.5 GB CTC model that NeMo
uses only for word timestamps and for chunking one long file; with it the model does not fit in
our 8 GB of RAM, so Canary is loaded with `restore_timestamps_model=False` (transcription
unchanged). The `.nemo` archives are streamed and unpacked once into the Hugging Face cache and
their weights memory-mapped (`baselines/pretrained/systems.py`).

### Table B — baselines we trained ourselves (vanilla architectures, our train split only)

<!-- BEGIN:table_b -->
| System | Family | Toolkit / recipe | Features | Train hours | Selected (on dev) | Decoding | Dev WER | Test WER | Test CER | Test WER (orth) | RTFx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `gmm_hmm` | B1 classical MFCC + GMM-HMM | own Python implementation (numpy/numba/torch) | 13 MFCC + d + dd (39), per-speaker CMVN | 14.76 | LM weight + insertion bonuses (grid) | Viterbi grapheme loop, char bigram LM, lm_weight=8.0, unit_insertion_bonus=2.0, word_boundary_bonus=4.0 (chosen on dev) | 97.51 | **97.80** | 56.49 | 98.50 | 724.5 |
| `e2e_ctc` | B2 CTC encoder (Conformer, from scratch) | own PyTorch recipe (torchaudio Conformer) | 80-dim log-mel, global CMVN, SpecAugment | 14.76 | epoch 6 of 6 | greedy CTC | 85.44 | **87.25** | 35.70 | 90.55 | 1674.89 |
| `e2e_aed` | B3a attention encoder-decoder (Conformer + Transformer decoder, from scratch) | own PyTorch recipe (torchaudio Conformer) | 80-dim log-mel, global CMVN, SpecAugment | 14.76 | epoch 6 of 6 | attention beam search (beam 5, length-normalized) | 119.17 | **121.79** | 76.40 | 123.17 | 6.76 |
| `e2e_hybrid` | B3b hybrid CTC/attention (Conformer + Transformer decoder, from scratch) | own PyTorch recipe (torchaudio Conformer) | 80-dim log-mel, global CMVN, SpecAugment | 14.76 | epoch 6 of 6 | attention beam search (beam 5, length-normalized) + CTC rescoring of the final beam (weight 0.3) | 89.51 | **92.90** | 52.87 | 98.66 | 6.37 |
| `e2e_rnnt` | B4 transducer RNN-T (Conformer + LSTM predictor, from scratch) | own PyTorch recipe (torchaudio Conformer) | 80-dim log-mel, global CMVN, SpecAugment | 14.76 | epoch 6 of 6 | greedy RNN-T (max 5 symbols/frame) | 68.96 | **72.26** | 34.90 | 78.47 | 51.44 |
<!-- END:table_b -->

- **B1 MFCC + GMM-HMM** (`baselines/trained/gmm_hmm.py`). Kaldi needs Linux; on our machine the
  Docker engine was broken and WSL had no networking, so we implemented the classical recipe
  ourselves: 13 Kaldi-compatible MFCC + Δ + ΔΔ, per-speaker CMVN, 3-state left-to-right grapheme
  HMMs (no Danish pronunciation lexicon was available), a word-boundary unit and a silence unit,
  diagonal GMMs with flat start, Viterbi training and mixture splitting up to 16 Gaussians per
  state, and Viterbi decoding over a grapheme loop with a character bigram LM trained on train
  transcripts only. LM weight, a per-grapheme insertion bonus and a word-boundary bonus were
  chosen on dev. Unlike Kaldi `tri1` it has no triphones, no lexicon and no word-level LM; for
  Danish, whose spelling is far from its pronunciation, graphemes are a weak unit.
- **B2–B4 neural families** (`baselines/trained/e2e.py`, configs `configs/e2e_*.yaml`). One
  recipe for all: 80-dim log-mel, global mean/variance from train, SpecAugment, 4× convolutional
  subsampling and an 8-layer Conformer encoder (d = 144), characters as output units. B2 CTC
  (`ctc_weight` 1.0); B3a pure attention encoder-decoder (`ctc_weight` 0.0); B3b hybrid
  CTC/attention (loss 0.3·CTC + 0.7·attention, CTC rescoring of the final beam); B4 RNN-T (LSTM
  prediction network + joint network, `torchaudio` RNN-T loss). The checkpoint is the epoch with
  the lowest **dev** WER under fast greedy decoding (for the hybrid: greedy decoding of its CTC
  head; `docs/decisions.md` D8). Trained from scratch on our train split, without pretrained
  weights, for **6 epochs** (the time limit of D10; more epochs would very likely help).

What Table B shows: with 6 epochs on ~15 h, none of our own systems produces usable Danish text;
their **CER** is the meaningful number (most characters are right, but enough are wrong that
most words contain an error). The transducer (B4) learned fastest; CTC (B2) reaches a similar
CER but drops many more words (deletions in Section 9); B1, with graphemes and no lexicon, gets
about half of the characters right; the pure attention model (B3a) has not learned to stop
decoding and repeats text, so its WER is above 100 % (Section 9). The attention models (B3a,
B3b) decode with beam search, which is much slower (RTFx column). All four would need many more epochs (the Polish version of this
recipe used 60) to be compared fairly; we report them as trained (D10).

### Table D — not run

| Baseline | Why not | Evidence |
|---|---|---|
| B6 HuBERT + CTC | no HuBERT model fine-tuned for Danish ASR exists on the Hugging Face Hub (searched 2026-11-21: `hubert danish`, `hubert-da`, `hubert_da`, `exp_w2v2t_da`; the `jonatasgrosman/exp_w2v2t_*_hubert_*` series has no Danish member). A bare HuBERT encoder is not an ASR system, and training a CTC head on it would be our own system, not a baseline. | `docs/language_support.md` |

## 8. Our contribution — fine-tuning `openai/whisper-small` on our train split

`contribution/train_whisper.py`, config `configs/contrib_whisper.yaml`: full fine-tuning with
Hugging Face `Seq2SeqTrainer`, Adafactor (AdamW's optimizer state does not fit in 4 GB next to the
model), fp16 autocast, gradient checkpointing, seed 1234, target = the cased and punctuated
manuscript line, dev WER (our normalizer, greedy decoding) every 150 steps, early stopping, and
the checkpoint with the lowest dev WER kept; **one epoch** over the train split (time limit, D10). The test set was decoded once, with the selected
checkpoint and exactly the decoding of B7, so the comparison isolates our training. The ΔWER
interval is the paired bootstrap against B7 (`openai/whisper-small` without our training).

<!-- BEGIN:table_c -->
| System | Base checkpoint @ revision | What we did | Train hours | Steps | Dev WER | Test WER | Test CER | Test WER (orth) | ΔWER vs. base (95% CI) | ΔCER vs. base (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|
| `whisper_small_ft` | [`openai/whisper-small`](https://huggingface.co/openai/whisper-small/tree/973afd24965f72e36ca33b3055d56a652f456b4d) @ `973afd2496` | full fine-tuning, adafactor, lr 1e-05, effective batch 16, early stopping on dev WER | 14.76 | 567 | 21.73 | **24.52** | 9.32 | 26.57 | -3.49 [-4.41, -2.58] | -0.84 [-1.27, -0.42] |
<!-- END:table_c -->

**Result: fine-tuning helped, on dev and on test.** One epoch over our train split (567 optimizer
steps; dev WER checked at steps 150, 300 and 450, and still falling at the last check, so the
checkpoint of step 450 was kept) lowered WER and CER on both dev and test. The paired bootstrap
interval of the test difference lies entirely below zero (Table C and the bootstrap table below),
so the gain is not an artefact of a few clips. Most of it is in-domain adaptation: the base model
already knows Danish, and one pass over NST-style read sentences teaches it the manuscript
spelling and the speakers' pronunciation (Section 9, "Fine-tuned vs. base Whisper"). Because dev
WER was still improving when training stopped, more epochs would very likely help further; we did
not run them (time limit, D10), and we changed nothing after seeing the test numbers.

Paired bootstrap results (A − B; negative = A is better):

<!-- BEGIN:bootstrap -->
| A | B | Split | ΔWER (A−B) | 95% CI | ΔCER (A−B) | 95% CI | Resamples |
|---|---|---|---|---|---|---|---|
| `whisper_small_ft` | `canary_1b_v2` | test | 14.57 | [13.60, 15.60] | 5.71 | [5.27, 6.15] | 2000 |
| `whisper_small_ft` | `whisper_small` | test | -3.49 | [-4.41, -2.58] | -0.84 | [-1.27, -0.42] | 2000 |
<!-- END:bootstrap -->

## 9. Error analysis and limitations

`python analysis/error_analysis.py` produces everything below; the tables are pasted by
`scripts/make_tables.py`. What we read from them:

- **Ranking.** The two NVIDIA models and the Danish wav2vec 2.0 model (B8, B9, B5) are far ahead;
  then our fine-tuned Whisper, the base Whisper and Qwen3-ASR; our own from-scratch systems are
  far behind (6 epochs, Section 7). The best baseline on dev, Canary, is also the best on test, and
  it is still clearly better than our fine-tuned Whisper (bootstrap table in Section 8).
- **WER vs. CER for Danish.** For every system CER is a fraction of WER: most wrong words are
  nearly right. For the strong systems a quarter or more of all substitutions are *ending* errors
  (same stem, different last letters: definite/plural suffixes such as *-en/-et/-ne/-er*, or verb
  endings), which WER counts as full errors. Letter-only confusions (æ/ø/å) are rare, so the models
  do write the Danish letters.
- **Dialect regions.** All systems rank the regions in a similar order: speakers from Vestjylland
  and Fyn are easiest, Vest- og Sydsjælland and Storkøbenhavn hardest. With one or two test
  speakers per region this is as much a speaker effect as a dialect effect (Limitations). Our
  fine-tuning lowered WER in every region of the test set. The test set has no speaker from
  Østjylland (the region appears in train and dev only), a consequence of dealing whole speakers
  to dev and test.
- **Clip length and gender.** Differences between female and male speakers are small for every
  system. Short clips (1–5 s) are slightly harder for the pretrained models, where one wrong word
  weighs more.
- **Fine-tuned vs. base Whisper** (last table below): fine-tuning removed substitutions, deletions
  and insertions alike, and more test clips got better than worse.
- **Our attention model (B3a)** has WER above 100 %: after 6 epochs its decoder has not learned to
  stop and repeats text (insertions in the error table). The hybrid (B3b), which adds the CTC loss,
  does not run away like this, which is the purpose of the CTC term.

<!-- BEGIN:analysis -->
**Error types on test** (normalized text). *Ending* = substitution where both words share a stem of at least 4 letters and differ only in the last ≤ 3 letters (in Danish mostly a definite or plural suffix: -en/-et/-ne/-er/-e, or a verb ending); *letter only* = the words are equal once æ ø å é are replaced by a o a e.

| System | Substitutions | Deletions | Insertions | Ending share of subs | Letter-only share of subs |
|---|---|---|---|---|---|
| `canary_1b_v2` | 1038 | 144 | 182 | 25.92 % | 0.77 % |
| `e2e_aed` | 11976 | 626 | 4098 | 0.05 % | 0.01 % |
| `e2e_ctc` | 9469 | 1957 | 538 | 4.32 % | 0.03 % |
| `e2e_hybrid` | 9093 | 834 | 2812 | 4.01 % | 0.09 % |
| `e2e_rnnt` | 6617 | 2905 | 386 | 7.69 % | 0.12 % |
| `gmm_hmm` | 8021 | 5310 | 79 | 0.35 % | 0.01 % |
| `parakeet_tdt_0.6b_v3` | 1643 | 246 | 184 | 29.46 % | 0.91 % |
| `qwen3_asr_0.6b` | 3335 | 545 | 388 | 19.31 % | 0.39 % |
| `wav2vec2_roest_315m_da` | 1493 | 300 | 126 | 30.21 % | 1.34 % |
| `whisper_small` | 2928 | 368 | 545 | 21.79 % | 0.48 % |
| `whisper_small_ft` | 2555 | 293 | 514 | 25.56 % | 0.94 % |

**Test WER (%) by clip duration** (test clips per bucket: 1-5 s: 379, 5-10 s: 543, 10-20 s: 53, 20-30 s: 0):

| System | 1-5 s | 5-10 s | 10-20 s |
|---|---|---|---|
| `canary_1b_v2` | 11.66 | 9.35 | 9.68 |
| `e2e_aed` | 154.43 | 112.45 | 100.26 |
| `e2e_ctc` | 86.54 | 87.23 | 89.54 |
| `e2e_hybrid` | 91.00 | 93.02 | 97.58 |
| `e2e_rnnt` | 70.19 | 73.01 | 72.34 |
| `gmm_hmm` | 97.82 | 97.65 | 98.88 |
| `parakeet_tdt_0.6b_v3` | 15.50 | 14.70 | 17.29 |
| `qwen3_asr_0.6b` | 33.12 | 29.90 | 35.00 |
| `wav2vec2_roest_315m_da` | 13.34 | 13.91 | 16.59 |
| `whisper_small` | 29.63 | 27.12 | 30.34 |
| `whisper_small_ft` | 23.55 | 24.57 | 26.97 |

**Test WER (%) by the speaker's dialect region** (NST `Region_of_Dialect`; test clips per region: Fyn: 162, Nordjylland: 162, Storkøbenhavn: 161, Sønderjylland: 162, Vest- og Sydsjælland: 162, Vestjylland: 166):

| System | Fyn | Nordjylland | Storkøbenhavn | Sønderjylland | Vest- og Sydsjælland | Vestjylland |
|---|---|---|---|---|---|---|
| `canary_1b_v2` | 8.05 | 10.61 | 10.12 | 10.16 | 13.10 | 7.84 |
| `e2e_aed` | 121.22 | 116.12 | 125.17 | 119.56 | 118.33 | 129.95 |
| `e2e_ctc` | 88.86 | 83.83 | 91.49 | 88.47 | 88.76 | 82.29 |
| `e2e_hybrid` | 95.51 | 91.31 | 95.48 | 89.93 | 92.34 | 92.75 |
| `e2e_rnnt` | 73.23 | 66.59 | 78.33 | 75.12 | 75.74 | 64.87 |
| `gmm_hmm` | 98.18 | 97.18 | 98.84 | 97.74 | 98.01 | 96.88 |
| `parakeet_tdt_0.6b_v3` | 11.94 | 17.02 | 17.11 | 15.21 | 16.56 | 13.16 |
| `qwen3_asr_0.6b` | 29.65 | 30.81 | 33.81 | 31.35 | 33.86 | 27.54 |
| `wav2vec2_roest_315m_da` | 12.41 | 14.55 | 15.81 | 13.97 | 16.73 | 10.75 |
| `whisper_small` | 24.35 | 27.09 | 33.14 | 27.85 | 31.65 | 24.38 |
| `whisper_small_ft` | 22.24 | 25.35 | 27.85 | 22.84 | 28.69 | 20.50 |

**Test WER (%) by speaker gender:**

| System | female | male |
|---|---|---|
| `canary_1b_v2` | 10.34 | 9.75 |
| `e2e_aed` | 117.95 | 123.70 |
| `e2e_ctc` | 86.17 | 87.79 |
| `e2e_hybrid` | 90.79 | 93.96 |
| `e2e_rnnt` | 70.90 | 72.93 |
| `gmm_hmm` | 97.49 | 97.95 |
| `parakeet_tdt_0.6b_v3` | 16.14 | 14.61 |
| `qwen3_asr_0.6b` | 31.05 | 31.16 |
| `wav2vec2_roest_315m_da` | 14.32 | 13.84 |
| `whisper_small` | 27.49 | 28.27 |
| `whisper_small_ft` | 24.13 | 24.71 |

**Cost on test** (RTFx = audio seconds / compute seconds; RTX 3050 Laptop 4 GB):

| System | RTFx | Peak GPU memory (MB) |
|---|---|---|
| `canary_1b_v2` | 33.71 | 2059.9 |
| `e2e_aed` | 6.76 | 2507.7 |
| `e2e_ctc` | 1674.89 | 2501.2 |
| `e2e_hybrid` | 6.37 | 2507.8 |
| `e2e_rnnt` | 51.44 | 2504.3 |
| `gmm_hmm` | 724.5 | 33.9 |
| `parakeet_tdt_0.6b_v3` | 129.0 | 2825.0 |
| `qwen3_asr_0.6b` | 14.08 | 2339.1 |
| `wav2vec2_roest_315m_da` | 118.85 | 1360.3 |
| `whisper_small` | 29.76 | 975.7 |
| `whisper_small_ft` | 41.64 | 975.7 |

**Fine-tuned vs. base Whisper** (`whisper_small_ft` − `whisper_small`, normalized text; a clip is *worse* if it has more word errors after fine-tuning):

| Split | WER base → fine-tuned | Δ substitutions | Δ deletions | Δ insertions | Clips worse | Clips better | Clips equal |
|---|---|---|---|---|---|---|---|
| dev | 24.46 → 21.73 | -309 | -37 | -7 | 260 | 391 | 282 |
| test | 28.01 → 24.52 | -373 | -75 | -31 | 272 | 449 | 254 |

Per-system top-20 substitution pairs: `analysis/substitutions_<system>.csv`; alignments of the 10 worst clips: `analysis/worst_<system>.txt`.
<!-- END:analysis -->

Test WER on the full test set and on test sentences that do not occur in train (identical by
construction, because the split is sentence-disjoint; kept as a check):

<!-- BEGIN:unseen -->
| System | Test WER (all) | Test WER (sentences not in train) | Utterances not in train |
|---|---|---|---|
| `wav2vec2_roest_315m_da` | 14.00 | 14.00 | 975 |
| `whisper_small` | 28.01 | 28.01 | 975 |
| `canary_1b_v2` | 9.95 | 9.95 | 975 |
| `parakeet_tdt_0.6b_v3` | 15.12 | 15.12 | 975 |
| `qwen3_asr_0.6b` | 31.13 | 31.13 | 975 |
| `gmm_hmm` | 97.80 | 97.80 | 975 |
| `e2e_ctc` | 87.25 | 87.25 | 975 |
| `e2e_aed` | 121.79 | 121.79 | 975 |
| `e2e_hybrid` | 92.90 | 92.90 | 975 |
| `e2e_rnnt` | 72.26 | 72.26 | 975 |
| `whisper_small_ft` | 24.52 | 24.52 | 975 |
<!-- END:unseen -->

**Limitations.**
1. **Less data and training than planned:** ~18 h in the splits instead of the 25 h registered,
   and our own B2–B4 models were trained for 6 epochs and the Whisper fine-tuning for one epoch,
   because the project had to be finished on the same day on a slow, metered connection
   (`docs/decisions.md` D10). B2–B4 are far from converged; their numbers show what each family
   learns in a few minutes of training, not what it can reach.
2. **Read speech from 2000:** NST is manuscript reading in quiet rooms with a close-talk
   microphone, much easier than conversational or broadcast Danish; the numbers do not transfer
   to spontaneous speech.
3. **dev/test are held-out speakers of NST's training part**, not NST's official test speakers
   (D4). Danish models fine-tuned on NST's training part could have seen them; our B5 model was
   not (CoRal), and the cards of B7–B10 do not name NST, but they do not list all their data.
4. **The reference is the manuscript line**, not a transcription of what was said; misreadings
   by the speaker count as system errors. The manual audit (Section 4) measures how often this
   happens.
5. **Small dev/test sets** (6 and 7 speakers): per-region results rest on one or two speakers
   per region, and confidence intervals are wide.
6. B1 is a Python re-implementation, not a Kaldi recipe (Section 7), and B6 could not be run
   (no Danish HuBERT checkpoint exists).

## 10. Reproduce

Environment: Python 3.11, CUDA 12.4, `pip install -r requirements.txt` (all versions pinned;
`torch`/`torchaudio` from `https://download.pytorch.org/whl/cu124`). GPU used: RTX 3050 Laptop
4 GB. Run from the repository root:

```bash
python scripts/01_download.py --cache /tmp/nst     # optional: rebuilds data/raw/audio (streams ~17 GB, stores ~3.3 GB)
python scripts/02_clean.py                         # data/raw -> data/cleaned + data/cleaning_log.csv
python scripts/03_make_splits.py                   # data/splits/{train,dev,test}.tsv
python scripts/04_split_stats.py                   # results/tables/split_stats.md
python scripts/05_audit.py sample                  # 100 random cleaned clips -> data/audit/ (manual audit)
python scripts/05_audit.py report                  # after listening: results/tables/audit.md
# pretrained baselines (B5, B7-B10): vanilla, nothing tuned, so dev and then test per model (D9)
for s in wav2vec2_roest_315m_da whisper_small qwen3_asr_0.6b parakeet_tdt_0.6b_v3 canary_1b_v2; do
  for sp in dev test; do
    python scripts/run_baseline.py --system $s --split $sp && python scripts/score.py --system $s --split $sp
  done
done
# trained baselines (B1-B4): train, select on dev, then decode dev and test
python -m baselines.trained.gmm_hmm train
python -m baselines.trained.gmm_hmm decode --split dev     # chooses LM weight / bonuses on dev
python -m baselines.trained.gmm_hmm decode --split test    # uses the dev choice
for c in ctc rnnt hybrid aed; do
  python -m baselines.trained.e2e train  --config configs/e2e_$c.yaml
  for sp in dev test; do python -m baselines.trained.e2e decode --config configs/e2e_$c.yaml --split $sp; done
done
# contribution
python contribution/train_whisper.py train  --config configs/contrib_whisper.yaml
for sp in dev test; do python contribution/train_whisper.py decode --config configs/contrib_whisper.yaml --split $sp; done
python scripts/score.py --system <name> --split <dev|test>  # after every decode above
python scripts/bootstrap.py --a whisper_small_ft --b whisper_small --split test
python scripts/collect_training_logs.py                    # exp/*/train_info.json -> results/training_logs/
python analysis/error_analysis.py
python scripts/make_tables.py
```

Model weights are not committed; the commands above regenerate them into `exp/` (git-ignored).
Predictions for every system and split are committed in `results/predictions/`, so all scores can
be recomputed with `scripts/score.py` without a GPU.

## 11. Repository map

| Path | What it is |
|---|---|
| `README.md` | this report |
| `LICENSE` | MIT license for **our code** |
| `DATA_LICENSE.md` | license and attribution of the NST data (CC0) |
| `requirements.txt` | pinned Python packages (one environment for all systems) |
| `pytest.ini` | test configuration (`slow` marker; no cache folder) |
| `.gitignore`, `.gitattributes` | keep caches, weights, `exp/` and the raw WAVs out of git; keep `data/` byte-exact |
| `configs/` | global seed, cleaning thresholds, training configs for B2–B4 and the contribution |
| `data/raw/` | `metadata.tsv`, `CHECKSUMS.sha256` and `sessions.txt` of the selected NST files; the WAVs themselves are rebuilt by `01_download.py` |
| `data/cleaned/` | cleaned 16-bit FLAC clips and `metadata.tsv` (normalized + orthographic transcript, speaker, sex, age, dialect) |
| `data/splits/` | `train.tsv`, `dev.tsv`, `test.tsv` |
| `data/audit/` | manual label audit: `audit_sample.tsv` (100 random cleaned clips), `listen.html` (listening page), `audit_results.csv` (once done) |
| `data/cleaning_log.csv` | every removed or fixed clip with reason code and detail |
| `scripts/` | data pipeline (`01`–`04`), manual audit (`05_audit.py`), `run_baseline.py`, `score.py`, `bootstrap.py`, `collect_training_logs.py`, `make_tables.py`, `check_submission.py` |
| `src/` | `normalize.py` (the one normalizer), `eval/metrics.py` (WER/CER), `asr_io.py`, `config.py` |
| `baselines/pretrained/` | B5, B7–B10 inference code with pinned model revisions |
| `baselines/trained/` | B1 GMM-HMM and B2–B4 neural recipes |
| `contribution/` | our Whisper fine-tuning |
| `results/predictions/` | hypotheses (`<split>.tsv`) and run info (`<split>.json`) per system |
| `results/metrics/` | scores per system (`<system>.json`) and bootstrap results |
| `results/training_logs/` | per-epoch dev scores and checkpoint choices of our trained systems |
| `results/tables/` | generated tables (also pasted into this README) |
| `analysis/` | error-analysis script and its outputs |
| `tests/` | pytest suite for the data pipeline, splits and evaluation |
| `docs/` | decision log, language-support check, dataset notes |
| `contributions/` | one file per member: `<NAME>_<STUDENT_ID>_<GITHUB_USERNAME>.md` |
| `exp/` | **not in git**: cached features, model weights, training logs |

## 12. Tests

`python -m pytest` (`-m "not slow"` skips the cleaning re-run; tests that need the raw WAVs are
skipped when `data/raw/audio/` has not been rebuilt).

- `tests/test_eval.py` — the lecture's worked examples (S=1, D=1, WER 0.3333, CER 0.2273;
  WER 3.0 / MER 0.75 / WIL 0.75 with insertions), pooled corpus WER, identical input → 0, empty
  hypothesis, normalizer idempotence / NFC / æ ø å kept / optional accents folded / Danish numbers /
  hyphens, per-utterance errors summing to the corpus score, bootstrap sanity.
- `tests/test_data_clean.py` — raw checksums, every cleaned clip 16 kHz mono and non-empty, no empty
  transcripts, no duplicate audio, every removed clip logged with a known reason, duration
  thresholds, no digits, Danish letters kept, no dictation commands left, cleaning deterministic.
- `tests/test_splits.py` — speakers disjoint, both sexes and most regions in dev and test, no
  dev/test sentence in train, same seed → same split (equal to the committed files), split sizes.

## 13. License

Our code: MIT (`LICENSE`). Data: NST Danish ASR Database, CC0, Nasjonalbiblioteket / Språkbanken
(`DATA_LICENSE.md`). The data license does not cover our scripts, and our code license does not
cover the data.

## Open items for the team

- Fill in `contributions/` (one file per member, committed from each member's own account) and
  the members table above.
- Confirm the mother-tongue rule and that no other group uses Danish or NST; log it in
  `docs/decisions.md`.
- Manual audit (Section 4): the 100 clips are already drawn. Open `data/audit/listen.html` in
  Chrome or Edge, listen to every clip, choose a verdict, click *Download CSV*, save it as
  `data/audit/audit_results.csv`, then run `python scripts/05_audit.py report` and
  `python scripts/make_tables.py`. The error rate is computed by the script, never typed in.
