1. What This Pipeline Does

This pipeline takes a basket of individual stocks, combines them into a single weighted portfolio return series, and generates an institutional-grade performance tearsheet — a two-page PDF report covering return, risk, drawdown, and distributional statistics for that portfolio as a whole.

It answers one question: given this specific combination of holdings and weights, how did the resulting portfolio actually perform, and how much risk did it take to get there.

2. Architecture Overview

The pipeline has three layers, each owned by a different library:

Layer	Responsibility	Library
Data acquisition	Pull historical daily prices for every ticker in the basket	yfinance
Portfolio construction	Convert prices to returns, apply weights, collapse into one return series	pandas, numpy
Reporting	Turn that single return series into a formatted PDF tearsheet	QF-Lib

QF-Lib is the reporting and statistics engine. It does not fetch data and does not know what a "stock" is — it only ever sees a single time-indexed series of returns. Everything upstream of that (which tickers, what weights) is the analyst's decision, encoded in plain Python before QF-Lib is ever called.

3. Environment Setup — Google Colab
3.1 Why Setup Requires Care Here

QF-Lib depends on an older, tightly pinned set of numerical libraries (older scipy, statsmodels) that were built against numpy's 1.x binary interface (ABI). Recent Colab images default to numpy 2.x. Installing QF-Lib without addressing this will not fail at install time — it fails later, on import, with:

ValueError: numpy.dtype size changed, may indicate binary incompatibility

This is a binary compatibility issue, not a bug in your code. It is resolved by pinning numpy before installing QF-Lib, and by restarting the Colab runtime once, so the Python process reloads with a consistent set of binaries.

3.2 Required Installation Sequence

Cell 1 — install (run once):

python
!apt-get update -qq
!apt-get install -y -qq libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 shared-mime-info poppler-utils

!pip install "numpy<2.0" -q
!pip install qf-lib yfinance pdf2image -q

Then: Runtime → Restart session. This step is not optional. Do not re-run Cell 1 after restarting.

3.3 Why Each Dependency Exists
Package	Purpose
libcairo2, libpango-1.0-0, libpangocairo-1.0-0, libgdk-pixbuf2.0-0, shared-mime-info	System libraries required by WeasyPrint, the PDF rendering engine QF-Lib uses internally to produce the tearsheet PDF
poppler-utils	Provides the pdfinfo / pdftoppm command-line binaries that pdf2image calls to convert the generated PDF into viewable images inside the notebook. pip install pdf2image installs only the Python wrapper — this system package is a separate, required dependency
numpy<2.0	Forces a numpy version compatible with QF-Lib's older pinned dependencies, avoiding the ABI mismatch described above
qf-lib	The core analytics and reporting engine
yfinance	Historical price data source
pdf2image	Converts the output PDF into displayable images for inline viewing in Colab
4. QF-Lib Concepts Used in This Pipeline
4.1 Settings

Every QF-Lib report requires a Settings object, built from two JSON files:

python
settings = Settings("config/settings.json", "config/secret_settings.json")

settings.json controls report cosmetics — company name, optional logo path, output directory. secret_settings.json exists for credentials (e.g. Bloomberg API keys) that this pipeline does not use, and is left as an empty JSON object.

4.2 SimpleReturnsSeries

QF-Lib does not operate on plain pandas Series — it uses its own typed container, SimpleReturnsSeries, which is a pandas Series subclass carrying additional metadata (frequency, naming conventions) that the reporting layer relies on internally.

python
strategy_series = SimpleReturnsSeries(data=portfolio_returns.values, index=portfolio_returns.index)
strategy_series.name = "Portfolio Name"

This is the single object every downstream tearsheet call consumes. Whatever weighting logic was applied happens before this line — by the time this object exists, the portfolio is already a single number stream, indistinguishable from a single stock's returns as far as QF-Lib is concerned.

4.3 PDFExporter and TearsheetWithoutBenchmark
python
pdf_exporter = PDFExporter(settings)

tearsheet = TearsheetWithoutBenchmark(
    settings=settings,
    pdf_exporter=pdf_exporter,
    strategy_series=strategy_series,
    title="Report Title"
)
tearsheet.build_document()
pdf_path = tearsheet.save(file_name="output.pdf")

TearsheetWithoutBenchmark produces a standalone performance report for a single return series, with no comparison line against a benchmark. QF-Lib also provides TearsheetWithBenchmark, which accepts a second return series (e.g. the S&P 500 via SPY) and overlays it on every chart, additionally producing rolling beta and rolling correlation panels. The pipeline documented here uses the former; the latter is a direct next step, requiring only a second SimpleReturnsSeries for the benchmark and swapping the class name.

5. Portfolio Construction Logic
5.1 From Individual Stocks to One Series
python
daily_returns = all_prices.pct_change().dropna(how="any")
weight_vector = np.array([WEIGHTS[t] for t in tickers_ordered])
portfolio_returns = daily_returns[tickers_ordered].dot(weight_vector)

Two design decisions embedded here are worth stating explicitly, since they materially affect every downstream number:

Rebalancing assumption. This calculation applies the specified weights fresh, every single day. This is equivalent to assuming the portfolio is rebalanced back to target weights daily — a modeling simplification, not a real-world trading behavior. A true buy-and-hold portfolio would let weights drift as constituent prices move, which is a materially different (and more complex) calculation.

dropna(how="any"). If any single ticker in the basket is missing a price on a given trading day, that entire day is dropped from every ticker's series, not just the one missing data. This keeps the weighted sum internally consistent — it guarantees the portfolio is never accidentally computed as if it were holding fewer positions than intended on a given day.

5.2 Weighting Schemes Used
Version	Logic
Equal-weight	Each of 12 tickers held at 1/12 (approximately 8.3%)
Custom-weight	NVDA and TSLA at 15% each, GOOGL and MSFT at 17.5% each, KO at 5%, V/MA/MCO at 10% each
Custom-weight with bonds	All equity weights scaled down proportionally by a fixed factor to make room for a fixed allocation to a bond ETF (e.g. 5-15% in TLT)
6. Metrics Glossary — What Each Statistic Means and How to Read It
Statistic	Definition	Interpretation Guidance
Total Return	Cumulative percentage growth over the entire period	The single-number summary of "how much did $1 become." Uninformative on its own about risk taken to get there
Annualised Return	Total return expressed as a compound annual growth rate	Allows comparison across periods of different length; the standard "return" figure for benchmarking
Annualised Volatility	Standard deviation of daily returns, scaled to an annual figure	The standard measure of total risk — how much the portfolio's value swings, in either direction
Upside / Downside Volatility	Volatility calculated separately for above-average and below-average return days	Distinguishes "good" volatility (large gains) from "bad" volatility (large losses) — a portfolio can have high total volatility that is mostly upside, which is a favorable condition rather than a risk
Sharpe Ratio	Annualised return divided by annualised (total) volatility	The standard risk-adjusted return measure. Penalizes all volatility, including favorable upside swings. A long-only equity portfolio Sharpe above 0.7 over a multi-year window that includes a bear market is a solid, not weak, result
Sortino Ratio	Annualised return divided by downside volatility only	A fairer risk-adjusted measure for asymmetric return distributions, since it does not penalize upside swings. A Sortino meaningfully higher than Sharpe indicates the portfolio's volatility skews favorably (more/larger up-moves than down-moves)
Calmar Ratio	Annualised return divided by maximum drawdown	Answers: how many years of typical return would it take to recover from the single worst historical loss. A ratio below 1.0 means the worst drawdown exceeds one year of typical gains — common for concentrated growth portfolios, and the clearest signal of structural fragility in the tearsheet
Omega Ratio	Ratio of total magnitude of gains to total magnitude of losses, relative to a threshold (typically zero)	A ratio above 1.0 indicates winning periods outweigh losing periods in aggregate magnitude
Gain to Pain Ratio	Sum of all positive returns divided by the absolute sum of all negative returns	Conceptually similar to Omega; a hedge-fund reporting convention. Values near 1.0 indicate a modest, persistent edge rather than dominant one-sided performance
5% CVaR (Conditional Value at Risk)	The average return on the worst 5% of days	Answers: on a genuinely bad day, how bad does it typically get. More informative than a simple worst-case number because it averages the entire bad tail rather than citing one outlier
Max Drawdown	The largest peak-to-trough decline in portfolio value over the period	The single most tangible risk number for most investors — the largest paper loss an investor would have had to sit through without selling
Avg Drawdown / Avg Drawdown Duration	The typical size and length of drawdown periods, not just the worst one	Indicates how often and how long the portfolio spends recovering, as distinct from the single worst event
Best / Worst Return	The single best and worst individual daily returns in the sample	Identifies tail-event magnitude at the daily level
Skewness	Asymmetry of the return distribution	Positive skewness (as seen in this portfolio, approximately 0.26) indicates a distribution with a longer right tail — more extreme up-days than extreme down-days, a favorable characteristic
Rolling Return / Rolling Volatility	The same return and volatility calculations, recomputed on a trailing window (126 trading days, approximately 6 months) throughout the period rather than once for the whole period	Reveals whether performance and risk were stable through time or concentrated in specific windows. A portfolio whose rolling return turns sharply negative at the same time rolling volatility spikes is exhibiting the exact pattern that damages Sharpe and Calmar ratios
6.1 A Note on Benchmark Comparison

TearsheetWithoutBenchmark, the class used throughout this pipeline, reports the portfolio in isolation. It does not calculate beta, alpha, or tracking error against any index. Any comparison to "the market" (for example, general Sharpe ratio benchmarks for the S&P 500) discussed alongside this pipeline's output is external context, not a number QF-Lib calculated. Obtaining an actual, calculated comparison requires switching to TearsheetWithBenchmark with a benchmark return series (e.g. SPY) supplied alongside the portfolio series.

7. Files Generated
File	Location	Contents
config/settings.json	Working directory	Report cosmetics configuration (company name, output directory)
config/secret_settings.json	Working directory	Empty credentials file, required by QF-Lib's Settings constructor
<name>_tearsheet.pdf	output/	Two-page PDF report: page 1 covers equity curve, monthly/annual return breakdowns, return distribution and normal Q-Q plot; page 2 covers the performance-vs-expectation cone chart, return quantiles, drawdown chart, skewness chart, and the full statistics table
8. Known Issues and Resolutions Encountered
Issue	Cause	Resolution
numpy.dtype size changed, may indicate binary incompatibility	numpy 2.x pre-installed in Colab conflicts with QF-Lib's older, numpy-1.x-compiled dependencies	Pin numpy<2.0 before installing QF-Lib, then restart the Colab runtime once
PDFInfoNotInstalledError: Unable to get page count	poppler-utils, the system-level PDF utility pdf2image depends on, was not installed via apt-get	Install poppler-utils via apt-get; no runtime restart required, since this is a system binary rather than a Python package
findfont: Font family 'Arial' not found	QF-Lib's default chart theme references Arial, a licensed font not present on Linux-based environments by default	Cosmetic only; matplotlib falls back to DejaVu Sans automatically and all charts render correctly. Can be suppressed with plt.rcParams['font.family'] = 'DejaVu Sans' if desired
Output path nested as output/output/...	Both settings.json's output_directory field and the report_dir argument to .save() were specifying a directory, and QF-Lib combined both	Set the output directory in only one of the two locations, not both
9. Suggested Next Steps
Switch to TearsheetWithBenchmark with SPY as the comparison series, to obtain an actual calculated Sharpe/Calmar/beta/correlation comparison against the broader market rather than relying on general context.
Test a buy-and-hold (non-rebalanced) version of the weighting logic, allowing weights to drift naturally, as a more realistic complement to the daily-rebalanced assumption used throughout this pipeline.
Evaluate a small, fixed allocation to a diversifying, low-equity-correlation asset (a short-to-intermediate duration bond ETF, or an alternative such as gold) sized to improve the Calmar ratio without materially diluting the portfolio's growth orientation.
Consider a market-cap-weighted variant as a third comparison point alongside the equal-weight and custom-weight versions already produced.
