# Take-Private Reverse LBO & Probabilistic Underwriting | Project Redwood

A private-equity case study that combines an Excel LBO model, a reverse-LBO maximum bid analysis, a hurdle solver, a Python probabilistic underwriting engine and a truly interactive browser dashboard.

## Headline outputs
- Seller ask: 8.5x EBITDA
- Base-case gross IRR / MOIC: 22.3% / 2.74x
- Deterministic max bid: 8.1x
- P(IRR >= 25%) at ask: 32.9%
- Risk-adjusted bid ceiling @ >=50% probability: 8.0x
- Risk-adjusted bid ceiling @ >=75% probability: 7.5x

## Main files
- `Take_Private_Reverse_LBO_Probabilistic_Underwriting_Model.xlsx`
- `Project_Redwood_Investment_Committee_Overview.pdf`
- `Project_Redwood_LinkedIn_Overview.pdf`
- `outputs/interactive_ic_dashboard.html`
- `run_risk_simulation.py`
- `src/risk_engine.py`

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_risk_simulation.py
```

Open `outputs/interactive_ic_dashboard.html` in your browser.
