# How to Explain This Project in an Interview

## One-line version
I built a fictional take-private case study that asks what a private equity sponsor can actually afford to pay for a business while still meeting return hurdles and protecting downside.

## What the project does
The project combines a traditional LBO model with a reverse LBO and a Python risk layer.

1. The LBO model starts with a seller asking price of 8.5x EBITDA.
2. It funds the acquisition with term loan debt, second-lien debt, management rollover and sponsor equity.
3. It projects five years of revenue, EBITDA, capex, working capital, taxes, interest and debt paydown.
4. It calculates exit equity value, sponsor proceeds, MOIC and IRR.
5. The reverse LBO then asks the more investment-relevant question: what is the highest price the sponsor can pay while still reaching a 25% IRR hurdle?
6. The Python engine runs 10,000 synthetic deal paths so the analysis does not rely only on one base case.

## Main conclusion
At the seller's 8.5x asking price, the base case produces approximately 22.3% gross IRR and 2.74x MOIC. The MOIC is strong, but the IRR does not reach the sponsor's 25% hurdle. The deterministic reverse LBO supports a maximum bid of around 8.1x, and the probabilistic analysis suggests lower risk-adjusted bid ceilings if the sponsor requires a high probability of hitting the return hurdle.

## Why it is more interesting than a standard LBO
A standard student LBO often stops at a single IRR output. This project focuses on underwriting discipline: price, leverage, return hurdles, probability of success and downside protection. It is closer to the question an investment committee would actually debate.

## What I would say if asked about AI assistance
I used AI assistance to help structure and implement parts of the project, but I reviewed the model logic, outputs and documentation and can explain the transaction mechanics and code flow. The project is fictional and educational.
