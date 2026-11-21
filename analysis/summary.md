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
