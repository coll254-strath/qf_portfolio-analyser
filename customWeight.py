"""
Custom-Weight Portfolio Tearsheet, With a Bond Allocation
===========================================================
Takes the custom-weighted equity basket, scales it down proportionally,
and adds a fixed allocation to a bond ETF (default: TLT, 20+ Year Treasuries)
to test whether it improves the Calmar ratio / reduces max drawdown.
 
Edit BOND_TICKER and BOND_WEIGHT below to test AGG, SHY, or a different
allocation size.
 
Setup required before running:
    !apt-get update -qq
    !apt-get install -y -qq libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 shared-mime-info poppler-utils
    !pip install "numpy<2.0" -q
    !pip install qf-lib yfinance pdf2image -q
    # Then: Runtime -> Restart session, before running this script.
"""
 
import json
import os
import shutil
 
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use("Agg")  # non-interactive backend, suitable for PDF generation
 
from qf_lib.settings import Settings
from qf_lib.containers.series.simple_returns_series import SimpleReturnsSeries
from qf_lib.documents_utils.document_exporting.pdf_exporter import PDFExporter
from qf_lib.analysis.tearsheets.tearsheet_without_benchmark import TearsheetWithoutBenchmark
from pdf2image import convert_from_path
from IPython.display import display
 
 
# --- Settings ---
os.makedirs("config", exist_ok=True)
with open("config/settings.json", "w") as f:
    json.dump({"company_name": "My Quant Desk", "output_directory": "output"}, f)
with open("config/secret_settings.json", "w") as f:
    json.dump({}, f)
settings = Settings("config/settings.json", "config/secret_settings.json")
os.makedirs("output", exist_ok=True)
 
# --- Base equity weights (same as portfolio_custom_weight.py) ---
EQUITY_WEIGHTS = {
    "NVDA":  0.15,
    "TSLA":  0.15,
    "GOOGL": 0.175,
    "MSFT":  0.175,
    "KO":    0.05,
    "V":     0.10,
    "MA":    0.10,
    "MCO":   0.10,
}
assert abs(sum(EQUITY_WEIGHTS.values()) - 1.0) < 1e-9
 
# --- Bond allocation ---
BOND_TICKER = "TLT"   # swap to "AGG" or "SHY" for a milder allocation
BOND_WEIGHT = 0.05    # fraction of total portfolio allocated to bonds
 
# --- Scale equity weights down proportionally to make room for bonds ---
scale_factor = 1.0 - BOND_WEIGHT
WEIGHTS = {t: w * scale_factor for t, w in EQUITY_WEIGHTS.items()}
WEIGHTS[BOND_TICKER] = BOND_WEIGHT
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, f"Weights sum to {sum(WEIGHTS.values())}"
 
print("Final weights:")
for t, w in WEIGHTS.items():
    print(f"  {t}: {w:.4f}")
 
# --- Download & align ---
tickers_ordered = list(WEIGHTS.keys())
print(f"\nDownloading {len(tickers_ordered)} tickers...")
all_prices = yf.download(tickers_ordered, period="5y", auto_adjust=True, progress=False)["Close"]
daily_returns = all_prices.pct_change().dropna(how="any")
print(f"Aligned dataset: {len(daily_returns)} trading days")
 
# --- Combine into ONE weighted portfolio series ---
weight_vector = np.array([WEIGHTS[t] for t in tickers_ordered])
portfolio_returns = daily_returns[tickers_ordered].dot(weight_vector)
 
strategy_series = SimpleReturnsSeries(data=portfolio_returns.values, index=portfolio_returns.index)
strategy_series.name = f"Mag7 + Monopoly + {BOND_TICKER} ({int(BOND_WEIGHT * 100)}% Bonds)"
 
# --- Tearsheet ---
pdf_exporter = PDFExporter(settings)
tearsheet = TearsheetWithoutBenchmark(
    settings=settings, pdf_exporter=pdf_exporter,
    strategy_series=strategy_series,
    title=f"Mag7 + Monopoly Basket + {BOND_TICKER} - {int(BOND_WEIGHT * 100)}% Bond Allocation"
)
tearsheet.build_document()
pdf_path = tearsheet.save(file_name="basket_with_bonds_tearsheet.pdf")
print(f"\nSaved: {pdf_path}")
 
# --- Display ---
poppler_path_exe = shutil.which("pdfinfo")
poppler_dir = os.path.dirname(poppler_path_exe) if poppler_path_exe else None
if not poppler_dir:
    print("WARNING: 'pdfinfo' not found. Ensure poppler-utils is installed.")
 
pages = convert_from_path(pdf_path, dpi=150, poppler_path=poppler_dir)
display(pages[0])
display(pages[1])
 
