# Language support of the course baselines for Danish (checked 2026-11-21)

Checked against the live model cards and the Hugging Face Hub API on 2026-11-21, not from memory.
Revisions are the Hub commit (`sha`) on that day; every run loads exactly that revision.

| Baseline | Model @ revision | Danish (da) | Evidence |
|---|---|---|---|
| B5 wav2vec 2.0 + CTC | [`CoRal-project/roest-v3-wav2vec2-315m`](https://huggingface.co/CoRal-project/roest-v3-wav2vec2-315m) @ `beb3e79024` | **yes** | Danish-only model: XLS-R 300M (wav2vec 2.0) fine-tuned with CTC on CoRal-v3 (Danish read-aloud and conversation, many dialects). No `jonatasgrosman/wav2vec2-large-xlsr-53-danish` exists (Hub search for `xlsr-53-danish`: no result). |
| B6 HuBERT + CTC | — | **no checkpoint** | Hub searches `hubert danish`, `hubert-da`, `hubert_da`, `exp_w2v2t_da` (and the ASR models matching `danish`, `dansk`, `-da-`) return no HuBERT model fine-tuned for Danish ASR. The `jonatasgrosman/exp_w2v2t_*_hubert_*` series has no Danish member. A bare HuBERT encoder is not a result, so B6 is not run (see README, Baselines). |
| B7 Whisper | [`openai/whisper-small`](https://huggingface.co/openai/whisper-small) @ `973afd2496` | yes | `da` in the card's language list; run with `language="danish"`, `task="transcribe"`. |
| B8 Canary | [`nvidia/canary-1b-v2`](https://huggingface.co/nvidia/canary-1b-v2) @ `d455706339` | yes | `da` in the card's language list; run with `source_lang="da"`, `target_lang="da"`. |
| B9 Parakeet | [`nvidia/parakeet-tdt-0.6b-v3`](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) @ `541d1f99c6` | yes | `da` in the card's language list (no language argument: the model detects the language). |
| B10 Qwen3-ASR | [`Qwen/Qwen3-ASR-0.6B`](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) @ `5eb144179a` | yes | card lists "Danish (da)"; run with `language="Danish"`. |

**Why the B5 checkpoint was chosen.** Several Danish wav2vec 2.0 CTC models exist. Some were
fine-tuned on NST's training part itself (for example `Alvenir/wav2vec2-base-da-ft-nst`), which is
where our dev/test speakers come from. We take the CoRal model because its card names only
CoRal-v3 as fine-tuning data, so it has not been trained on our test speakers, and it is
the most downloaded Danish wav2vec 2.0 model from a research project with a public training recipe.
The repository also ships a 3-gram language model; we do not use it (greedy CTC, like every other
CTC system here).

**Training data of the pretrained models vs. NST.** None of the cards of B7-B10 names NST or
Språkbanken. They do not list all their data, so overlap cannot be ruled out; see README,
Limitations.

**Licenses:** Whisper MIT; Canary and Parakeet CC-BY-4.0; Qwen3-ASR Apache-2.0; CoRal roest
custom license adapted from OpenRAIL-M (allows research use). None restricts our evaluation.
