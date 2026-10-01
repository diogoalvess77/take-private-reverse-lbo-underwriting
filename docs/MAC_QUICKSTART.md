# Mac Quickstart

## 1. Open Terminal and enter the project folder
Type `cd ` (with a space after it), drag the project folder from Finder into Terminal, then press Enter.

## 2. Check Python
```bash
python3 --version
```
Use Python 3.10 or later.

## 3. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install the project dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 5. Run the full underwriting analysis
```bash
python run_risk_simulation.py --paths 10000 --seed 77
```

## 6. Open the interactive dashboard
```bash
open outputs/interactive_ic_dashboard.html
```

## 7. Run the automated tests
```bash
python -m pytest -q
```
You should see `15 passed`.

## 8. Open the Excel model
```bash
open Take_Private_Reverse_LBO_Probabilistic_Underwriting_Model.xlsx
```

The Python engine and Excel model use the same synthetic base-case assumptions and are reconciled through the automated tests.
