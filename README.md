# Aspect Insight

**Generative aspect-based sentiment analysis: from raw reviews to what customers praise and criticise.**

Aspect Insight reads a review and writes out every opinion in it as an **(aspect, category, opinion, sentiment)** quadruple, then turns many reviews into a dashboard that tells a business what to fix first, with evidence.

| Review | Aspect | Category | Opinion | Sentiment |
|---|---|---|---|---|
| *The battery life is stellar, but the plastic build feels cheap.* | battery life | Battery - operation performance | stellar | positive |
| | plastic build | Laptop - design features | cheap | negative |
| *It died after two hours.* | *(implicit)* | Battery - operation performance | died | negative |

It is trained and evaluated on [MEMD-ABSA](https://github.com/NUSTM/MEMD-ABSA) (18,104 sentences, five domains: books, clothing, hotels, laptops and restaurants) and compares three ways of using generative models under one evaluation protocol.

![Analyze a review](docs/screenshots/step3.png)

## Highlights

- **Matches the published results.** One Flan-T5-base model that is told the review's domain is within 2.5 F1 points of the best published models on four of five domains (exact-match ACOS F1, mean of three seeds). Qwen2.5-1.5B with LoRA exceeds the best published Restaurant score.
- **A diagnosed and fixed failure.** Without the domain, 26 % of a single model's Laptop predictions used categories from other domains. Naming the domain in the input cut this to 0.4 % and raised Laptop ACOS F1 from 22.7 to 34.8.
- **Fine-tuning versus prompting.** Flan-T5 (49.7 ACOS F1, 35 ms per sentence) ties Qwen2.5-1.5B LoRA (50.2, not a significant difference) and beats prompting Qwen2.5-7B with five retrieved examples (30.4) by about 20 points.
- **Rare-class study.** Five ways of handling the rare Neutral class (2.2 % of opinions), including balanced bagging and LLM-generated training data, with McNemar tests per seed and temperature scaling for calibrated confidences.
- **Grounded summaries.** The dashboard's written summary is produced by an LLM from facts computed in code, and every number, "X vs Y" pair and "N out of M" claim in it is checked against those facts before it is shown.

## The web application

| Page | What it does |
|---|---|
| **Analyze** | One review and its domain: aspects highlighted in their sentiment colour, the quadruple table, and a calibrated confidence from a second model that checks each sentiment |
| **Batch insights** | Many reviews (paste, upload a .txt or .csv, or pick a demo file): a checked summary, "fix first" and "keep doing" topics with real quotes and a link to every review behind each number, sentiment by category, CSV export |
| **Compare** | Two sets of reviews side by side (two branches, two products, before and after an update): biggest differences in complaints, charts and a checked comparison summary |
| **Model lab** | One sentence through several generators with greedy, beam-search or sampling decoding, showing the raw generated text and latency |
| **Evaluation** | Test-set results, the comparison with the published results and the error analysis |

<p>
  <img src="docs/screenshots/step5.png" width="49%" alt="Summary and priorities">
  <img src="docs/screenshots/step6.png" width="49%" alt="Comparing two restaurant branches">
</p>

## How it works

```
review + domain ─► Flan-T5-base ─► "[A] battery life [C] battery - operation performance [O] stellar [S] positive [SSEP] ..."
                                        │
                                        ▼
                            parser ─► quadruples ─► DeBERTa-v3-small sentiment check (temperature-scaled)
                                        │
                                        ▼
                    counts per topic ─► Qwen2.5-1.5B-Instruct writes a summary ─► every number is verified
```

| Component | Model | Training |
|---|---|---|
| Quadruple generator (deployed) | Flan-T5-base, 248 M parameters | full fine-tuning, domain named in the input |
| Quadruple generator (compared) | Qwen2.5-1.5B-Instruct | LoRA, rank 16, 18.5 M trainable parameters |
| Prompting baseline | Qwen2.5-7B-Instruct | none: instruction, category list and 5 TF-IDF-retrieved examples |
| Sentiment check | DeBERTa-v3-small | class-weighted cross-entropy, temperature scaling |
| Summary writer | Qwen2.5-1.5B-Instruct | none: phrases facts computed in code |

## Quick start

Requirements: Python 3.10 or newer, Node.js 18 or newer, and optionally an NVIDIA GPU.

```bash
python -m venv .venv
.venv\Scripts\activate              # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python scripts/prepare_data.py      # builds data/processed/ from data/raw/
python -m pytest                    # 31 tests
```

### Run the web application

The trained weights are not stored in the repository (about 1.3 GB). Train them with the notebooks below, then place them under `outputs/runs/`:

| Path | Needed for |
|---|---|
| `outputs/runs/t5/all_domains_tagged/model/seed42/model` | all pages |
| `outputs/runs/classifiers/class_weights/seed42/model` (with `dev_probs.npy` one level up) | all pages |
| `outputs/runs/t5/all_domains/model/seed42/model` | Model lab (optional) |
| `outputs/runs/qwen/all_domains_tagged/model/seed42/model` | Model lab (optional) |

```bash
cd frontend
npm install
npm run build
cd ..
python -m uvicorn backend.app:app --port 8000
```

Open http://localhost:8000. The first start loads the models (about 30 seconds). For frontend development, run `npm run dev` in `frontend/` (port 5173, with API calls proxied to port 8000).

API endpoints: `GET /api/health`, `/api/domains`, `/api/samples`, `/api/demo`, `/api/demo/{name}`, `/api/results` and `POST /api/analyze`, `/api/batch`, `/api/compare`, `/api/summary`.

## Training and evaluation

The notebooks run the scripts on Google Colab. Copy the repository to Google Drive, open a notebook, set `PROJECT_DIR` in its first cell to the folder's Drive path, choose a GPU runtime and run all cells. Every script reads its settings from `configs/`, skips runs that already have results, and accepts `--limit` and `--epochs` for quick smoke tests.

| Notebook | What it runs | Results in |
|---|---|---|
| `01_prepare_data` | `scripts/prepare_data.py` | `data/processed/` |
| `02_sentiment_classifiers` | five class-imbalance methods, three seeds | `outputs/results/classifiers/` |
| `03_t5_quad_generator` | Flan-T5 per domain, all domains, cross-domain, decoding strategies | `outputs/results/t5/` |
| `04_qwen_quad_generator` | Flan-T5 with the domain in the input, Qwen2.5-1.5B LoRA, prompting baselines | `outputs/results/t5/`, `qwen/`, `prompting/` |
| `05_neutral_augmentation` | LLM-generated Neutral data, with and without verification | `outputs/results/classifiers/` |

The evaluation summaries used by the dashboard are included in `outputs/results/`.

## Repository layout

| Path | Contents |
|---|---|
| `src/absa/` | Data handling, models, metrics, analysis and inference |
| `scripts/` | Data preparation, training, evaluation and data generation |
| `configs/` | Experiment settings |
| `notebooks/` | Colab runners |
| `backend/` | FastAPI service |
| `frontend/` | React, Vite, Tailwind CSS and Recharts single-page app |
| `data/raw/MEMD-ABSA/` | Original dataset |
| `data/processed/` | Processed splits, category inventory and LLM-generated Neutral data |
| `data/demo/` | Simulated review files for trying the dashboard |
| `outputs/results/` | Evaluation results |
| `docs/screenshots/` | Screenshots of the web application |
| `tests/` | Unit tests |

## Demo data

`data/demo/` contains 200 **simulated** reviews in 12 CSV files for trying the dashboard: two branches of a fictional restaurant, a fictional laptop before and after a firmware update, three well-known laptops (described only with traits widely reported in public reviews), a hotel, a kurta and a novel. None of them is a real customer review, and every row is marked as simulated.

## Dataset and references

- H. Cai, N. Song, Z. Wang, Q. Xie, Q. Zhao, K. Li, S. Wu, S. Liu, J. Yu and R. Xia. *MEMD-ABSA: A Multi-Element Multi-Domain Dataset for Aspect-Based Sentiment Analysis.* arXiv:2306.16956, 2023.
- H. W. Chung et al. *Scaling Instruction-Finetuned Language Models.* arXiv:2210.11416, 2022.
- E. J. Hu et al. *LoRA: Low-Rank Adaptation of Large Language Models.* ICLR, 2022.
- Qwen Team. *Qwen2.5 Technical Report.* arXiv:2412.15115, 2024.
- P. He, J. Gao and W. Chen. *DeBERTaV3.* ICLR, 2023.
- C. Guo, G. Pleiss, Y. Sun and K. Q. Weinberger. *On Calibration of Modern Neural Networks.* ICML, 2017.
