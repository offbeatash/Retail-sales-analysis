# Retail Sales Analysis

An end-to-end electronics retail analytics project with a Streamlit dashboard, SQLite backend, machine-learning revenue insights, notebook-based data generation, report exports, and automated project checks.

The project is designed for local analysis and portfolio/GitHub review. Sensitive and bulky runtime artifacts such as databases, CSV data, Power BI files, generated reports, and chart images are intentionally ignored by Git.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Setup](#setup)
- [Database Workflow](#database-workflow)
- [Running the Dashboard](#running-the-dashboard)
- [Frontend](#frontend)
- [Backend](#backend)
- [Database Schema](#database-schema)
- [Machine Learning](#machine-learning)
- [Reports and Exports](#reports-and-exports)
- [Tests](#tests)
- [GitHub Readiness and Security](#github-readiness-and-security)
- [Troubleshooting](#troubleshooting)

## Features

- Admin registration and login for dashboard access.
- Secure password hashing with PBKDF2-HMAC and per-user salts.
- SQLite-backed analytics using live SQL queries.
- KPI cards for orders, revenue, and profit.
- Regional revenue and profit analysis.
- Monthly performance view with satisfactory vs. below-average classification.
- Tree-based feature-importance model for revenue drivers.
- Form for adding new sales records to the local database.
- Raw data explorer with category filtering.
- Quick insights for top product, best month, and next-month baseline forecast.
- Crystal Reports package generator with PDF sections, SQL view definitions, schema notes, and setup guidance.
- Notebook workflow for synthetic electronics sales data generation, EDA, model comparison, chart generation, and forecasting.
- Unit and Selenium smoke tests for project quality and dashboard behavior.

## Architecture

```text
Notebook workflow
  Electronics_Sales_Analysis.ipynb
      -> generates electronics_sales_2024.csv
      -> creates analysis charts and ML outputs

  data.ipynb
      -> reads electronics_sales_2024.csv
      -> creates sales_database.db

Application workflow
  app.py
      -> Streamlit UI
      -> SQLite queries and inserts
      -> admin auth table
      -> ML feature-importance training
      -> report ZIP generation

Tests
  tests/pytest_tests.py
      -> compile checks, DB checks, GitHub hygiene checks

  tests/selenium_smoke_test.py
      -> launches Streamlit and verifies core UI flows in Chrome
```

## Project Structure

```text
.
|-- app.py
|-- Electronics_Sales_Analysis.ipynb
|-- data.ipynb
|-- requirements.txt
|-- README.md
|-- .gitignore
|-- tests/
|   |-- pytest_tests.py
|   `-- selenium_smoke_test.py
|-- reports/                     # ignored generated reports
|-- images/                      # ignored generated chart images
|-- electronics_sales_2024.csv    # ignored local dataset
|-- sales_database.db             # ignored local SQLite database
`-- Retail_sales_analysis.pbix    # ignored local Power BI file
```

## Tech Stack

Frontend:

- Streamlit
- Altair charts
- Streamlit metrics, forms, dataframes, tabs, sidebars, and download buttons

Backend:

- Python
- SQLite
- Pandas
- Matplotlib PDF generation
- Zipfile-based report packaging

Data and ML:

- Pandas
- NumPy
- Scikit-learn
- XGBoost
- Seaborn
- Matplotlib
- Plotly

Testing:

- Python `unittest`
- Selenium WebDriver
- Chrome headless browser testing
- Git-based repository hygiene checks

## Setup

Use Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Database Workflow

The Streamlit app expects a local SQLite file named `sales_database.db`.

To create it from the notebooks:

1. Open and run `Electronics_Sales_Analysis.ipynb`.
2. Confirm it creates `electronics_sales_2024.csv`.
3. Open and run `data.ipynb`.
4. Confirm it creates `sales_database.db`.

The CSV and database are local runtime artifacts and should stay out of Git.

## Running the Dashboard

```powershell
streamlit run app.py
```

On first launch:

1. Open the local Streamlit URL printed in the terminal.
2. Register the first admin account.
3. Log in with that admin account.
4. Use the dashboard sections for analysis, data entry, raw data exploration, and reporting.

## Frontend

The frontend is implemented in `app.py` with Streamlit.

Main UI sections:

- `Admin Access` - login and registration tabs.
- `Executive Summary` - total orders, revenue, and profit KPIs.
- `Sales by Region` - regional table and bar chart.
- `Monthly Performance` - monthly revenue classification chart.
- `Tree-Based Feature Importance` - model-driven revenue driver chart and table.
- `Add New Sales Record` - form that inserts a record into SQLite.
- `Explore Raw Data` - category filter and raw sales table.
- `Crystal Report Generator` - downloadable ZIP of generated PDF reports and setup files.
- `Quick Insights` - top product, best month, and baseline forecast options.

## Backend

The backend logic is also contained in `app.py`.

Key backend responsibilities:

- Opens SQLite connections through `get_connection()`.
- Initializes the `admin_users` table if it does not exist.
- Hashes admin passwords with `hashlib.pbkdf2_hmac`.
- Verifies passwords with `hmac.compare_digest`.
- Runs cached SQL reads with `st.cache_data`.
- Inserts new sales records into `sales_data`.
- Builds PDF report sections from query results.
- Packages report assets into a downloadable ZIP file.
- Trains tree-based models on current sales data for feature importance.

## Database Schema

Local database file:

```text
sales_database.db
```

Main sales table:

```text
sales_data
|-- Order_ID TEXT
|-- Date TEXT
|-- Month TEXT
|-- Quarter TEXT
|-- Product_Name TEXT
|-- Category TEXT
|-- Brand TEXT
|-- Unit_Price REAL
|-- Discount_Percent INTEGER
|-- Selling_Price REAL
|-- Quantity INTEGER
|-- Revenue REAL
|-- Cost REAL
|-- Profit REAL
|-- Profit_Margin_Pct REAL
|-- City TEXT
|-- Region TEXT
|-- Sales_Channel TEXT
|-- Payment_Method TEXT
|-- Return_Flag TEXT
|-- Customer_Segment TEXT
`-- Festival_Season INTEGER
```

Admin authentication table:

```text
admin_users
|-- id INTEGER
|-- username TEXT
|-- password_hash TEXT
|-- salt TEXT
`-- created_at TEXT
```

The app stores password hashes and salts, not plaintext passwords.

## Machine Learning

The notebook includes a broader ML workflow for revenue prediction:

- Feature engineering from dates, product attributes, channel data, customer segment, return flag, and festival season.
- Categorical encoding for model training.
- Train/test split.
- Model comparison across:
  - Linear Regression
  - Random Forest Regressor
  - Gradient Boosting Regressor
  - XGBoost Regressor
- Metrics:
  - R2
  - MAE
  - RMSE
- Actual vs. predicted chart.
- Tree-based feature-importance chart.
- Three-month revenue forecast.
- Monthly satisfaction check against average monthly revenue.

The Streamlit app includes a live ML section that trains Random Forest and Gradient Boosting models against the current SQLite data and displays grouped feature importance.

## Reports and Exports

The dashboard can generate a Crystal Reports support package as a ZIP file.

Included ZIP contents:

- PDF executive summary.
- PDF regional performance report.
- PDF monthly performance report.
- PDF category performance report.
- PDF top-products report.
- PDF channel/payment report.
- PDF city summary.
- PDF raw sales sample.
- `schema.txt` with database schema details.
- `crystal_report_queries.sql` with optional SQLite views.
- `README_Crystal_Report_Setup.md` with Crystal Reports setup notes.

Generated exports are ignored by Git.

## Tests

Run the project-standard tests:

```powershell
python -m unittest tests.pytest_tests
```

These tests check:

- Python syntax compilation.
- Required SQLite database and `sales_data` table.
- Required sales schema columns.
- Dashboard SQL query validity.
- Secure admin table structure.
- Expected security and report-generation features in `app.py`.
- `.gitignore` coverage for sensitive local files.
- Sensitive local files are not tracked by Git.
- Common secret patterns are not present in tracked text files.

Run the Selenium smoke test:

```powershell
python tests\selenium_smoke_test.py
```

The Selenium test:

- Starts Streamlit on a free local port.
- Registers a temporary admin user.
- Logs in.
- Verifies key dashboard sections render.
- Checks KPI values against SQLite totals.
- Verifies charts, tables, category filtering, and quick insights.
- Removes the temporary admin user after the test.

Chrome must be installed for the Selenium smoke test.

## GitHub Readiness and Security

The repository is configured to keep local data, secrets, generated files, and bulky artifacts out of Git.

Ignored examples:

- `.env`
- `.env.*`
- `secrets.toml`
- `.streamlit/secrets.toml`
- credential JSON files
- private keys and certificates
- `*.db`
- `*.csv`
- `*.pbix`
- `reports/`
- `*.png`
- `*.pptx`
- `*.pdf`
- `*.xlsx`
- `*.zip`
- Python caches and test caches

Before pushing:

```powershell
git status --short
git ls-files --cached --ignored --exclude-standard
python -m unittest tests.pytest_tests
```

Expected result:

- No secrets are tracked.
- Local database and CSV files are not tracked.
- Generated report/image files are not tracked.
- Tests pass.

## Troubleshooting

`sales_database.db is required for local testing`

Run the notebook workflow first so the local database exists.

`ModuleNotFoundError`

Install dependencies:

```powershell
pip install -r requirements.txt
```

`Streamlit app opens to Admin Access`

This is expected. Register the first admin user, then log in.

`Selenium cannot find Chrome`

Install Google Chrome or update the Chrome binary path in `tests/selenium_smoke_test.py`.

`Permission denied while compiling Python files`

Clear local cache folders or redirect bytecode output:

```powershell
$env:PYTHONPYCACHEPREFIX="$PWD\.pycache-check"
python -m unittest tests.pytest_tests
```
