# Constrained Domain Decoding Evaluation (Seed 42, Zero Retraining)

| Model | Mode | Overall ACOS F1 | Laptop ACOS F1 | Laptop Wrong-Domain (%) | Overall Wrong-Domain (%) | ms/sentence |
|---|---|---:|---:|---:|---:|---:|
| Flan-T5-base, no domain | Unconstrained | 47.04 | 22.12 | 28.16 | 8.76 | 36.38 |
| Flan-T5-base, no domain | Constrained | 50.10 | 31.60 | 0.00 | 0.00 | 339.58 |
| Flan-T5-base + domain | Unconstrained | 49.63 | 34.32 | 0.48 | 0.19 | 33.17 |
| Flan-T5-base + domain | Constrained | 49.65 | 34.32 | 0.00 | 0.00 | 316.83 |
