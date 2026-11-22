# Decoding strategies

3,583 test sentences, model `model`.

| Strategy | ACOS F1 | Precision | Recall | AOS F1 | Malformed segments | ms/sentence |
|---|---|---|---|---|---|---|
| Greedy | 47.18 | 46.99 | 47.38 | 63.18 | 1.0 | 35.5 |
| Beam search (4 beams) | 47.22 | 46.67 | 47.78 | 63.24 | 1.0 | 45.3 |
| Sampling, T=0.7, top-p=0.9 | 46.42 | 46.20 | 46.65 | 62.81 | 1.0 | 36.3 |
| Sampling, T=1.0, top-p=1.0 | 44.79 | 44.51 | 45.07 | 61.51 | 2.0 | 36.8 |
| Self-consistency (5 samples, T=0.7, majority vote) | 47.70 | 48.42 | 46.99 | 63.15 | 1.0 | 183.3 |
