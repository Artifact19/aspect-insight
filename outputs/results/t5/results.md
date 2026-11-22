# Flan-T5-base: quadruple extraction results

Micro-F1 (%) with exact matching. Mean ± standard deviation over seeds where several seeds were run.

## Comparison with published results (ACOS, Table 9 of the MEMD-ABSA paper)

| Domain | Best published | T5-Paraphrase | T5-index | Ours: per-domain models | Ours: one model, all domains | Ours: one model, domain in input |
|---|---|---|---|---|---|---|
| Books | 41.71 (T5-index) | 39.00 | 41.71 | 39.00 ± 0.77 | 38.71 ± 2.39 | 39.45 ± 1.33 |
| Clothing | 41.26 (T5-Paraphrase) | 41.26 | 37.55 | 40.42 ± 0.61 | 39.32 ± 1.59 | 40.86 ± 1.07 |
| Hotel | 69.22 (T5-index) | 66.89 | 69.22 | 65.54 ± 1.56 | 67.16 ± 1.94 | 67.68 ± 0.50 |
| Restaurant | 56.49 (T5-index) | 56.31 | 56.49 | 55.53 ± 0.68 | 54.59 ± 0.50 | 55.54 ± 0.64 |
| Laptop | 43.57 (T5-Paraphrase) | 43.57 | 40.38 | 33.97 ± 0.77 | 22.73 ± 0.77 | 34.84 ± 0.70 |

## Comparison with published results (AOS, Table 9)

| Domain | Best published | Ours: per-domain models | Ours: one model, all domains | Ours: one model, domain in input |
|---|---|---|---|---|
| Books | 53.46 (T5-index) | 48.54 ± 0.59 | 51.40 ± 2.49 | 49.49 ± 1.77 |
| Clothing | 69.63 (T5-index) | 68.93 ± 1.11 | 68.72 ± 0.78 | 70.19 ± 1.15 |
| Hotel | 77.98 (T5-index) | 74.08 ± 1.63 | 76.81 ± 1.14 | 76.21 ± 0.50 |
| Restaurant | 65.12 (T5-index) | 61.06 ± 0.82 | 62.49 ± 0.15 | 61.85 ± 0.97 |
| Laptop | 67.88 (T5-Paraphrase) | 52.72 ± 0.28 | 54.67 ± 0.78 | 55.80 ± 0.95 |

## One model for all domains: every sub-task (all test sentences)

| Model | AE | ASPE | CS | AOS | ACS | ACOS | ACOS precision | ACOS recall |
|---|---|---|---|---|---|---|---|---|
| one model, all domains | 78.89 ± 0.55 | 74.44 ± 0.32 | 62.93 ± 0.63 | 63.01 ± 0.75 | 53.75 ± 0.71 | 46.62 ± 0.92 | 46.74 ± 0.28 | 46.52 ± 1.55 |
| one model, domain in input | 78.85 ± 0.54 | 74.35 ± 0.38 | 68.29 ± 0.80 | 62.79 ± 0.53 | 58.18 ± 0.57 | 49.74 ± 0.30 | 50.37 ± 0.66 | 49.16 ± 1.21 |

## Categories from the wrong domain (single models)

Share of predicted quadruples whose category exists only in another domain, and ACOS F1 before and after such quadruples are removed.

| Model | Domain | Wrong-domain categories (%) | ACOS F1 | ACOS F1, wrong-domain removed |
|---|---|---|---|---|
| one model, all domains | Books | 4.37 ± 0.40 | 38.71 ± 2.39 | 39.56 ± 2.41 |
| one model, all domains | Clothing | 6.75 ± 1.02 | 39.32 ± 1.59 | 40.69 ± 1.61 |
| one model, all domains | Hotel | 3.37 ± 0.82 | 67.16 ± 1.94 | 68.30 ± 1.72 |
| one model, all domains | Restaurant | 3.65 ± 0.77 | 54.59 ± 0.50 | 55.59 ± 0.30 |
| one model, all domains | Laptop | 26.28 ± 1.61 | 22.73 ± 0.77 | 26.20 ± 0.87 |
| one model, domain in input | Books | 0.12 ± 0.12 | 39.45 ± 1.33 | 39.47 ± 1.32 |
| one model, domain in input | Clothing | 0.00 ± 0.00 | 40.86 ± 1.07 | 40.86 ± 1.07 |
| one model, domain in input | Hotel | 0.14 ± 0.05 | 67.68 ± 0.50 | 67.73 ± 0.52 |
| one model, domain in input | Restaurant | 0.13 ± 0.06 | 55.54 ± 0.64 | 55.57 ± 0.64 |
| one model, domain in input | Laptop | 0.37 ± 0.17 | 34.84 ± 0.70 | 34.90 ± 0.68 |

## Transfer to other domains (ACOS F1)

| Training data | Books | Clothing | Hotel | Restaurant | Laptop |
|---|---|---|---|---|---|
| Trained on the same domain | 39.00 ± 0.77 | 40.42 ± 0.61 | 65.54 ± 1.56 | 55.53 ± 0.68 | 33.97 ± 0.77 |
| Trained on all five domains | 38.71 ± 2.39 | 39.32 ± 1.59 | 67.16 ± 1.94 | 54.59 ± 0.50 | 22.73 ± 0.77 |
| Trained on all five domains, domain in input | 39.45 ± 1.33 | 40.86 ± 1.07 | 67.68 ± 0.50 | 55.54 ± 0.64 | 34.84 ± 0.70 |
| Trained on Laptop + Restaurant | 5.80 | 1.29 | 21.18 | 57.16 | 27.19 |
| Trained on the other four domains | 0.93 | 2.56 | 21.53 | 10.71 | 0.18 |

## Transfer to other domains (AOS F1)

| Training data | Books | Clothing | Hotel | Restaurant | Laptop |
|---|---|---|---|---|---|
| Trained on the same domain | 48.54 ± 0.59 | 68.93 ± 1.11 | 74.08 ± 1.63 | 61.06 ± 0.82 | 52.72 ± 0.28 |
| Trained on all five domains | 51.40 ± 2.49 | 68.72 ± 0.78 | 76.81 ± 1.14 | 62.49 ± 0.15 | 54.67 ± 0.78 |
| Trained on all five domains, domain in input | 49.49 ± 1.77 | 70.19 ± 1.15 | 76.21 ± 0.50 | 61.85 ± 0.97 | 55.80 ± 0.95 |
| Trained on Laptop + Restaurant | 34.07 | 50.04 | 59.45 | 62.70 | 53.66 |
| Trained on the other four domains | 38.61 | 53.44 | 64.80 | 52.11 | 48.43 |

### Leave-one-domain-out vs the paper (AOS, sentences with explicit elements only; approximate)

| Held-out domain | Paper (T5-Paraphrase) | Ours |
|---|---|---|
| Books | 51.78 | 42.74 |
| Clothing | 60.39 | 55.36 |
| Hotel | 72.60 | 66.81 |
| Restaurant | 61.47 | 52.20 |
| Laptop | 61.77 | 52.39 |

## ACOS recall by element type (one model, all domains)

| Gold quadruples with | Count | Recall (%) |
|---|---|---|
| explicit aspect | 4,098 | 50.49 ± 1.55 |
| explicit opinion | 4,384 | 51.67 ± 1.13 |
| implicit aspect | 1,381 | 34.47 ± 1.62 |
| implicit opinion | 1,095 | 25.54 ± 3.22 |

## Error analysis (all_domains, seed 42)

2,887 gold quadruples were not produced exactly; 1,309 predictions had no matching gold quadruple.

| Missed because of | Count | Share |
|---|---|---|
| category | 764 | 26.5% |
| opinion | 336 | 11.6% |
| sentiment | 70 | 2.4% |
| aspect found, several elements wrong | 445 | 15.4% |
| aspect missed | 1,272 | 44.1% |

## Runs

| Experiment | Run | Seed | Best epoch | Train (min) | ms/sentence | Malformed segments |
|---|---|---|---|---|---|---|
| all_domains | model | 42 | 12 | 44.0 | 34.44 | 1 |
| all_domains | model | 153 | 5 | 25.2 | 31.9 | 3 |
| all_domains | model | 650 | 11 | 43.8 | 33.63 | 1 |
| all_domains_tagged | model | 42 | 5 | 36.4 | 34.28 | 2 |
| all_domains_tagged | model | 153 | 6 | 40.5 | 38.6 | 3 |
| all_domains_tagged | model | 650 | 6 | 40.5 | 31.34 | 0 |
| cross_laptop_restaurant | model | 42 | 10 | 21.1 | 38.11 | 3 |
| in_domain | Books | 42 | 5 | 4.0 | 43.89 | 3 |
| in_domain | Books | 153 | 5 | 3.8 | 30.58 | 0 |
| in_domain | Books | 650 | 4 | 3.4 | 34.91 | 0 |
| in_domain | Clothing | 42 | 8 | 4.3 | 30.43 | 0 |
| in_domain | Clothing | 153 | 11 | 5.5 | 29.22 | 0 |
| in_domain | Clothing | 650 | 15 | 7.1 | 26.69 | 0 |
| in_domain | Hotel | 42 | 7 | 6.1 | 37.09 | 0 |
| in_domain | Hotel | 153 | 4 | 4.3 | 36.37 | 1 |
| in_domain | Hotel | 650 | 7 | 6.2 | 33.65 | 0 |
| in_domain | Laptop | 42 | 4 | 4.9 | 36.25 | 1 |
| in_domain | Laptop | 153 | 6 | 6.2 | 31.86 | 0 |
| in_domain | Laptop | 650 | 8 | 7.7 | 33.08 | 2 |
| in_domain | Restaurant | 42 | 7 | 9.3 | 31.51 | 0 |
| in_domain | Restaurant | 153 | 8 | 10.2 | 38.96 | 0 |
| in_domain | Restaurant | 650 | 9 | 11.0 | 38.27 | 0 |
| leave_one_out | without_Books | 42 | 10 | 34.3 | 33.76 | 0 |
| leave_one_out | without_Clothing | 42 | 9 | 33.1 | 29.44 | 0 |
| leave_one_out | without_Hotel | 42 | 6 | 22.7 | 38.94 | 1 |
| leave_one_out | without_Laptop | 42 | 11 | 35.6 | 30.08 | 0 |
| leave_one_out | without_Restaurant | 42 | 9 | 27.9 | 41.0 | 0 |
