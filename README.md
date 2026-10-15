# SentinelPay

A transaction simulator that shows how a bank can verify and validate a payment before it goes through.

This is a portfolio project, not a product.
It started as a school project that reproduced a fraud detection paper.
It grew into a working pipeline that you can click through and watch decide.
It does not model the real world, such as one customer using many devices.

## How it works

Every transaction passes two layers.

| Layer | What it does | Status |
| --- | --- | --- |
| 1. Deterministic rules | Checks the account, the country, and known bad IPs, devices, cards, and email domains | Done |
| 2. Model score | Scores the fraud probability of transactions that pass Layer 1 | Planned |

Layer 1 returns `APPROVE`, `REVIEW`, or `DECLINE`, and the name of the rule that decided.
It reads from Redis and falls back to Postgres if Redis is down.
See [doc/deterministic-risk.md](doc/deterministic-risk.md) for the rules, the failure behavior, the mock accounts, and the trade-offs.

Until Layer 2 exists, an `APPROVE` only means that no rule fired.
The UI says so.

## Try it

You need Docker.

1. Copy `.env.example` to `.env`.
   The defaults work for local development.
   `.env` is ignored by git, so keep real secrets there and nowhere else.
2. Start the stack and load the mock data:

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.seed_mock
```

3. Open the frontend, pick an account, pick a transaction, and read the verdict.
   The API docs are at `http://localhost:8000/docs`.

Pick a clean account to see the country and entity rules fire.
Pick a frozen, restricted, or flagged account to see an account rule win.

Run the backend tests with `pytest backend/tests`.

## Layer 2 plan

1. Retrain the Deep Boosting Decision Tree (DBDT) model and save its parameters to a `.pkl` file.
2. Serve it next to the current LightGBM model.
3. Compare the two on fraud rate and score quality.

The threshold sliders in the UI are for Layer 2, so they have no effect yet.

## Repository layout

| Path | Contents |
| --- | --- |
| `backend/` | FastAPI service: routes, Layer 1 risk checks, SQLModel tables, seed script, tests |
| `frontend/` | React and Vite simulator UI |
| `src/` | DBDT research code: soft decision tree, DBDT, baselines, evaluation |
| `main.ipynb` | Experiments: preprocessing, training, threshold tuning, plots |
| `doc/` | Layer 1 design notes and the project report |
| `sources/`, `presentation/` | The reference paper and the slides |

## Research background

The model work reproduces parts of *Efficient Fraud Detection Using Deep Boosting Decision Trees* (Xu, Wang, Liao, Wang, 2023).
It trains on the [Kaggle credit card fraud dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud), which is highly imbalanced.
The notebook uses a stratified subset, applies SMOTE to the training split only, and tunes the decision threshold on a validation split.
It reports AUC, H-measure, F1, precision, and recall.

`src/pdsca.py` is a simplified prototype, not the full PDSCA algorithm from the paper.
Setup for the notebook: `pip install -r requirements.txt`, then run `main.ipynb` from top to bottom.

The results are in [the project report](doc/Deep%20Boosting%20Decision%20Trees%20for%20Credit%20Card%20Fraud%20Detection%20(report).pdf).

## Acknowledgment

Built on the paper and the public dataset above.
