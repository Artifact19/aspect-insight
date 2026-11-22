# Qwen2.5-1.5B LoRA: quadruple extraction results

Micro-F1 (%) with exact matching. Mean ± standard deviation over seeds where several seeds were run.

## Comparison with published results (ACOS, Table 9 of the MEMD-ABSA paper)

| Domain | Best published | T5-Paraphrase | T5-index | Ours: one model, domain in input |
|---|---|---|---|---|
| Books | 41.71 (T5-index) | 39.00 | 41.71 | 38.61 ± 0.67 |
| Clothing | 41.26 (T5-Paraphrase) | 41.26 | 37.55 | 38.08 ± 0.17 |
| Hotel | 69.22 (T5-index) | 66.89 | 69.22 | 68.35 ± 1.20 |
| Restaurant | 56.49 (T5-index) | 56.31 | 56.49 | 56.72 ± 0.82 |
| Laptop | 43.57 (T5-Paraphrase) | 43.57 | 40.38 | 36.93 ± 0.17 |

## Comparison with published results (AOS, Table 9)

| Domain | Best published | Ours: one model, domain in input |
|---|---|---|
| Books | 53.46 (T5-index) | 51.82 ± 1.02 |
| Clothing | 69.63 (T5-index) | 70.73 ± 0.38 |
| Hotel | 77.98 (T5-index) | 77.65 ± 0.19 |
| Restaurant | 65.12 (T5-index) | 63.34 ± 0.37 |
| Laptop | 67.88 (T5-Paraphrase) | 58.16 ± 0.18 |

## One model for all domains: every sub-task (all test sentences)

| Model | AE | ASPE | CS | AOS | ACS | ACOS | ACOS precision | ACOS recall |
|---|---|---|---|---|---|---|---|---|
| one model, domain in input | 80.23 ± 0.34 | 76.01 ± 0.22 | 68.28 ± 0.16 | 64.46 ± 0.20 | 58.63 ± 0.25 | 50.24 ± 0.04 | 50.48 ± 0.14 | 50.00 ± 0.06 |

## Categories from the wrong domain (single models)

Share of predicted quadruples whose category exists only in another domain, and ACOS F1 before and after such quadruples are removed.

| Model | Domain | Wrong-domain categories (%) | ACOS F1 | ACOS F1, wrong-domain removed |
|---|---|---|---|---|
| one model, domain in input | Books | 0.46 ± 0.30 | 38.61 ± 0.67 | 38.70 ± 0.71 |
| one model, domain in input | Clothing | 0.05 ± 0.09 | 38.08 ± 0.17 | 38.09 ± 0.19 |
| one model, domain in input | Hotel | 0.34 ± 0.17 | 68.35 ± 1.20 | 68.43 ± 1.25 |
| one model, domain in input | Restaurant | 0.06 ± 0.00 | 56.72 ± 0.82 | 56.74 ± 0.82 |
| one model, domain in input | Laptop | 0.40 ± 0.23 | 36.93 ± 0.17 | 36.97 ± 0.22 |

## ACOS recall by element type (one model, all domains)

| Gold quadruples with | Count | Recall (%) |
|---|---|---|
| explicit aspect | 4,098 | 51.37 ± 0.19 |
| explicit opinion | 4,384 | 54.44 ± 0.09 |
| implicit aspect | 1,381 | 45.67 ± 0.40 |
| implicit opinion | 1,095 | 31.87 ± 0.48 |

## Error analysis (all_domains_tagged, seed 42)

2,740 gold quadruples were not produced exactly; 1,219 predictions had no matching gold quadruple.

| Missed because of | Count | Share |
|---|---|---|
| category | 663 | 24.2% |
| opinion | 376 | 13.7% |
| sentiment | 64 | 2.3% |
| aspect found, several elements wrong | 380 | 13.9% |
| aspect missed | 1,257 | 45.9% |

## Runs

| Experiment | Run | Seed | Best epoch | Train (min) | ms/sentence | Malformed segments |
|---|---|---|---|---|---|---|
| all_domains_tagged | model | 42 | 3 | 30.8 | 113.55 | 2 |
| all_domains_tagged | model | 153 | 3 | 30.4 | 109.59 | 3 |
| all_domains_tagged | model | 650 | 3 | 30.6 | 114.67 | 7 |
