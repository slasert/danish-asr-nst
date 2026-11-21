| System | Base checkpoint @ revision | What we did | Train hours | Steps | Dev WER | Test WER | Test CER | Test WER (orth) | ΔWER vs. base (95% CI) | ΔCER vs. base (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|
| `whisper_small_ft` | [`openai/whisper-small`](https://huggingface.co/openai/whisper-small/tree/973afd24965f72e36ca33b3055d56a652f456b4d) @ `973afd2496` | full fine-tuning, adafactor, lr 1e-05, effective batch 16, early stopping on dev WER | 14.76 | 567 | 21.73 | **24.52** | 9.32 | 26.57 | -3.49 [-4.41, -2.58] | -0.84 [-1.27, -0.42] |
