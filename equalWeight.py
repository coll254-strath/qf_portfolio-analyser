""" Setup required before running :
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
 
# --- The Basket ---
TICKERS = {
    "GOOGL": "Alphabet", "NVDA": "Nvidia", "MSFT": "Microsoft", "TSLA": "Tesla",
    "V": "Visa", "MA": "Mastercard", "MCO": "Moody's", "SPGI": "S&P Global",
    "UNP": "Union Pacific", "WM": "Waste Management", "ISRG": "Intuitive Surgical", "KO": "Coca-Cola",
}
 
# --- Download & align ---
print(f"Downloading {len(TICKERS)} tickers...")
all_prices = yf.download(list(TICKERS.keys()), period="5y", auto_adjust=True, progress=False)["Close"]
daily_returns = all_prices.pct_change().dropna(how="any")
print(f"Aligned dataset: {len(daily_returns)} trading days across all {len(TICKERS)} names")
 
# --- Combine into ONE equal-weighted portfolio series ---
weights = np.array([1 / len(TICKERS)] * len(TICKERS))
portfolio_returns = daily_returns[list(TICKERS.keys())].dot(weights)
 
strategy_series = SimpleReturnsSeries(data=portfolio_returns.values, index=portfolio_returns.index)
strategy_series.name = "Mag7 + Monopoly Basket (Equal-Weight)"
 
# --- Tearsheet ---
pdf_exporter = PDFExporter(settings)
tearsheet = TearsheetWithoutBenchmark(
    settings=settings, pdf_exporter=pdf_exporter,
    strategy_series=strategy_series,
    title="Mag7 + Monopoly Basket - Equal-Weight Portfolio"
)
tearsheet.build_document()
pdf_path = tearsheet.save(file_name="basket_equal_weight_tearsheet.pdf")
print(f"\nSaved: {pdf_path}")
 
# --- Display ---
poppler_path_exe = shutil.which("pdfinfo")
poppler_dir = os.path.dirname(poppler_path_exe) if poppler_path_exe else None
if not poppler_dir:
    print("WARNING: 'pdfinfo' not found. Ensure poppler-utils is installed.")
 
pages = convert_from_path(pdf_path, dpi=150, poppler_path=poppler_dir)
display(pages[0])
display(pages[1])
 
