Custom-weighted portfolio analytics using QF-Lib. Combines a basket of stocks into a single weighted return series and generates an institutional-grade PDF tearsheet covering return, risk, drawdown, and distributional statistics.
 
## Requirements
 
- Google Colab (or any environment with internet access to Yahoo Finance)
- Python 3.x
## Setup
 
Run once, in order:
 
```python
!apt-get update -qq
!apt-get install -y -qq libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 shared-mime-info poppler-utils
 
!pip install "numpy<2.0" -q
!pip install qf-lib yfinance pdf2image -q
```
 
Then: **Runtime → Restart session** before running any other cell. This step is required — QF-Lib's dependencies conflict with the numpy version Colab preloads by default, and a restart is the only way to clear it.
 
## Usage
 
1. Define the basket and target weights:
```python
WEIGHTS = {
    "NVDA":  0.15,
    "TSLA":  0.15,
    "GOOGL": 0.175,
    "MSFT":  0.175,
    "KO":    0.05,
    "V":     0.10,
    "MA":    0.10,
    "MCO":   0.10,
}
```
 
Weights must sum to 1.0.
 
2. Run the pipeline script. It will:
   - Download historical prices for every ticker
   - Combine them into a single weighted portfolio return series
   - Generate a two-page PDF tearsheet
   - Display both pages inline in the notebook
3. Find the generated report in `output/`.
## Project Structure
 
```
config/
  settings.json           # report cosmetics (company name, output directory)
  secret_settings.json    # empty credentials file, required by QF-Lib
output/
  <name>_tearsheet.pdf    # generated two-page report
```
 
## Adjusting the Portfolio
 
- **Change holdings or weights**: edit the `WEIGHTS` dictionary. No other code changes needed.
- **Add a bond or other asset**: add its ticker to `WEIGHTS` with a nonzero allocation, scale existing weights down proportionally so the total still sums to 1.0.
- **Compare against a benchmark**: swap `TearsheetWithoutBenchmark` for `TearsheetWithBenchmark` and supply a second `SimpleReturnsSeries` (e.g. SPY).
## Troubleshooting
 
| Error | Fix |
|---|---|
| `numpy.dtype size changed, may indicate binary incompatibility` | Pin `numpy<2.0` before installing `qf-lib`, then restart the Colab runtime |
| `PDFInfoNotInstalledError` | Install `poppler-utils` via `apt-get` |
| `findfont: Font family 'Arial' not found` | Cosmetic warning only, safe to ignore |
 
## Full Documentation
 
See `DOCUMENTATION.md` for the complete metrics glossary, architecture explanation, and design rationale.
 
