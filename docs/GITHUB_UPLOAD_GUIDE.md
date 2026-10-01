# GitHub Upload Guide - Browser Method

This guide assumes you do not want to use Terminal.

## 1. Create the repository
On GitHub, choose **New repository**.

- Repository name: `take-private-reverse-lbo-underwriting`
- Description: `Take-private LBO, reverse-LBO bid ceiling and probabilistic private equity underwriting case study.`
- Visibility: **Public**
- Add README: **Off**
- .gitignore: **None**
- License: **None** (the project already includes a license)

Create the repository.

## 2. Open the GitHub-ready folder on your Mac
Unzip the GitHub-ready package. Open the folder `take-private-reverse-lbo-underwriting`.

Inside it you should see files such as:

```text
README.md
LICENSE
.gitattributes
.gitignore
Take_Private_Reverse_LBO_Probabilistic_Underwriting_Model.xlsx
Project_Redwood_Investment_Committee_Overview.pdf
Project_Redwood_Investment_Committee_Overview.pptx
run_risk_simulation.py
requirements.txt
pyproject.toml
src/
tests/
outputs/
docs/
.github/
```

## 3. Show hidden files
In Finder press:

`Command + Shift + .`

This makes `.gitattributes` and `.gitignore` visible.

## 4. Select everything inside the folder
Click inside the folder and press:

`Command + A`

Select the contents of the folder, not the outer folder itself.

## 5. Upload to GitHub
In the empty repository choose **uploading an existing file** or **Add file -> Upload files**.

Drag the selected files and folders into GitHub. Keep folders such as `src`, `tests`, `outputs` and `docs` intact - you do not need to open them individually.

## 6. Commit
Use this commit message:

`Initial release of Project Redwood underwriting case study`

Commit directly to the `main` branch.

## 7. Configure About
Description:

`Take-private LBO, reverse-LBO bid ceiling and probabilistic private equity underwriting case study.`

Topics:

`private-equity` `lbo` `financial-modeling` `valuation` `investment-banking` `python` `monte-carlo` `risk-analysis` `mna` `corporate-finance`

## 8. Final checks
The repository home page should display the README automatically. Confirm that:

- the first chart loads;
- `src/`, `tests/`, `outputs/` and `docs/` are visible;
- the Excel model and PDF overview are present;
- the **Actions** tab shows the automated test workflow after the first commit;
- GitHub's language bar is not dominated by generated HTML/PDF files (the included `.gitattributes` marks generated assets appropriately).

## 9. Optional: pin the repository
On your GitHub profile, add the repository to your pinned repositories so recruiters see it quickly.
