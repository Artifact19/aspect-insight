# In-context prompting baselines (no training)

| Run | Model | Shots | Examples | ACOS F1 | P | R | AOS F1 | AE F1 | Malformed | Prompt tokens | ms/sentence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen1.5b_5shot_similar | Qwen2.5-1.5B-Instruct | 5 | similar | 22.59 | 21.83 | 23.41 | 33.45 | 58.17 | 231 | 581 | 278.1 |
| qwen7b_5shot_random | Qwen2.5-7B-Instruct | 5 | random | 17.32 | 16.31 | 18.46 | 27.55 | 56.21 | 67 | 625 | 821.5 |
| qwen7b_5shot_similar | Qwen2.5-7B-Instruct | 5 | similar | 30.36 | 27.78 | 33.47 | 41.19 | 65.20 | 68 | 581 | 791.0 |
| qwen7b_zero_shot | Qwen2.5-7B-Instruct | 0 | - | 0.07 | 0.64 | 0.04 | 1.25 | 3.45 | 5581 | 303 | 473.0 |

## ACOS F1 per domain

| Run | Books | Clothing | Hotel | Laptop | Restaurant |
|---|---|---|---|---|---|
| qwen1.5b_5shot_similar | 11.72 | 12.35 | 36.78 | 20.77 | 23.54 |
| qwen7b_5shot_random | 8.36 | 7.58 | 23.46 | 13.36 | 24.79 |
| qwen7b_5shot_similar | 16.75 | 21.32 | 46.20 | 23.69 | 34.95 |
| qwen7b_zero_shot | 0.00 | 0.00 | 0.15 | 0.00 | 0.11 |
