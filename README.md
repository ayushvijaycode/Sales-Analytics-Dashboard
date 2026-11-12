# Sales Analytics Dashboard

A Streamlit application for uploading, validating, cleaning, filtering, and analyzing sales data.

## Features
- Upload CSV, Excel (`.xlsx`), and JSON records.
- Inspect dimensions, columns, inferred data types, missing values, and duplicate rows.
- Normalize headers/text, coerce common sales measures to numeric, and parse common date fields.
- Choose a missing-value strategy and remove duplicate records.
- Interactive filters for available Region, Category, Segment, Ship Mode, State, and date range fields.
- Five live KPIs: Total Sales, Total Profit, unique Total Orders, Total Quantity Sold, and Profit Margin.
- Interactive Plotly charts and reusable statistical-summary functions.
- Download the cleaned, filtered data as CSV.

## Run locally

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Deploy on Streamlit Community Cloud
1. Create a GitHub repository (public is simplest for Community Cloud deployment).
2. Upload `app.py`, `requirements.txt`, and this `README.md` to the repository root. Do not commit private or sensitive data.
3. Sign in at https://share.streamlit.io/ using GitHub and authorize access to the repository.
4. Select **Create app**, choose the repository, branch, and `app.py` as the main file.
5. Select **Deploy** and wait for the build to finish.
6. Open the generated `*.streamlit.app` URL. Upload the sample CSV and verify the quality report, filters, KPIs, charts, and CSV download.

## Data expectations
The five requested KPIs require columns named `Sales`, `Profit`, `Order ID`, and `Quantity`. The dashboard adapts filters and charts to the columns present. Common date fields named `Order Date` and `Ship Date` are parsed automatically.
