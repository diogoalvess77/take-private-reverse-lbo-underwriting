# Methodology - Take-Private Reverse LBO & Probabilistic Underwriting

**Case name:** Project Redwood  
**Status:** fictional educational case study using synthetic assumptions.

## 1. Transaction framing
The case is set up like a simplified take-private process. The seller asks for an entry valuation of 8.5x LTM EBITDA. A financial sponsor evaluates whether that price can meet a 25% gross IRR hurdle and a 2.5x gross MOIC hurdle while remaining financeable.

## 2. Sources & Uses
Enterprise value is calculated as entry EV / EBITDA multiplied by LTM EBITDA. Uses include purchase price, minimum cash, transaction fees and financing fees. Sources include Term Loan B, second-lien debt and sponsor equity, with management rolling over 8% of the equity capitalisation.

## 3. Operating model
Revenue is projected over a five-year hold period using explicit annual growth assumptions. EBITDA margin expands gradually. D&A, capex and working capital are modelled as percentages of revenue. Cash taxes are calculated on EBIT. Free cash flow before debt service equals EBITDA less capex, change in working capital and cash taxes.

## 4. Debt waterfall
The financing package contains a Term Loan B, second-lien debt and an undrawn revolver. The Term Loan B pays floating-rate cash interest, amortises at 1% of original principal and receives a 75% cash sweep on excess cash. The revolver is drawn only if the company needs liquidity to restore minimum cash. Interest coverage and RCF usage are tracked for downside review.

## 5. Sponsor returns
At exit, enterprise value equals exit EBITDA multiplied by the exit EV / EBITDA multiple. Net debt is deducted to calculate equity value. The sponsor receives its post-rollover share of exit equity. Gross MOIC equals sponsor exit proceeds divided by sponsor initial equity. Gross IRR is calculated over the five-year hold period.

## 6. Reverse LBO
The reverse LBO works backwards from sponsor exit proceeds and target returns. The model calculates the maximum initial sponsor equity that can be paid while still meeting the IRR and MOIC hurdles. That equity value is then converted into a maximum enterprise value and entry multiple after debt financing, fees and rollover.

## 7. Hurdle solver
The hurdle solver asks what would need to improve if the sponsor insisted on paying the seller's 8.5x ask. It isolates three levers: required exit EBITDA, required exit multiple and required debt paydown. These are decision-framing alternatives, not simultaneous assumptions.

## 8. Probabilistic underwriting
The Python engine creates 10,000 synthetic deal paths. Each path shocks revenue growth, EBITDA margin, interest rates and exit valuation through correlated factors. Every path runs through the same operating and debt waterfall as the deterministic case. The outputs include IRR, MOIC, minimum interest coverage, revolver draw, exit net debt and hurdle outcomes.

## 9. Risk-adjusted bid ceiling
The risk layer also recalculates sponsor returns across a grid of entry multiples. This shows the probability of achieving a 25% IRR at each price. The highest price at which the model clears a chosen probability threshold becomes the risk-adjusted bid ceiling.

## 10. Limitations
The model is deliberately simplified. It excludes purchase accounting, detailed deferred tax attributes, full covenant packages, PIK instruments, refinancing assumptions, dividend recaps, add-on acquisitions, management option pools, real market calibration and legal diligence. The probabilities are synthetic and illustrative rather than empirical forecasts.
