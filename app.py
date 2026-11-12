import json
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sales Analytics Dashboard", page_icon="📊", layout="wide")

NUMERIC_CANDIDATES = ["Sales", "Profit", "Quantity", "Discount"]
DATE_CANDIDATES = ["Order Date", "Ship Date"]


def load_data(uploaded_file):
    """Read CSV, Excel, or JSON uploads into a DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file, engine="openpyxl")
    if name.endswith(".json"):
        raw = json.load(uploaded_file)
        if isinstance(raw, list):
            return pd.json_normalize(raw)
        if isinstance(raw, dict):
            for key in ("data", "records", "items"):
                if isinstance(raw.get(key), list):
                    return pd.json_normalize(raw[key])
            return pd.json_normalize(raw)
        raise ValueError("JSON must contain an array of records or an object.")
    raise ValueError("Unsupported file type. Upload CSV, XLSX, or JSON.")


def normalize_data(df):
    """Standardize headers, trim text, coerce common numeric/date fields."""
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    for col in out.select_dtypes(include=["object", "string"]).columns:
        out[col] = out[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        out[col] = out[col].replace({"": pd.NA, "N/A": pd.NA, "NA": pd.NA, "null": pd.NA, "None": pd.NA})
    for col in NUMERIC_CANDIDATES:
        if col in out.columns:
            cleaned = out[col].astype("string").str.replace(r"[$,]", "", regex=True)
            out[col] = pd.to_numeric(cleaned, errors="coerce")
    for col in DATE_CANDIDATES:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def preprocess_data(df, fill_method, remove_duplicates):
    out = normalize_data(df)
    if remove_duplicates:
        out = out.drop_duplicates()
    for col in out.columns:
        if not out[col].isna().any():
            continue
        if fill_method == "Drop rows with missing values":
            out = out.dropna(subset=[col])
        elif fill_method == "Fill numeric with median / text with mode":
            if pd.api.types.is_numeric_dtype(out[col]):
                out[col] = out[col].fillna(out[col].median())
            elif pd.api.types.is_datetime64_any_dtype(out[col]):
                out[col] = out[col].fillna(out[col].mode().iloc[0] if not out[col].mode().empty else pd.NaT)
            else:
                mode = out[col].mode(dropna=True)
                if not mode.empty:
                    out[col] = out[col].fillna(mode.iloc[0])
        # Keep missing values is intentionally a valid choice.
    return out


def numeric_summary(df):
    numeric = df.select_dtypes(include="number")
    return numeric.describe().T if not numeric.empty else pd.DataFrame()


def money(value):
    return f"₹{value:,.2f}"


def show_quality(df, title):
    st.subheader(title)
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{df.shape[0]:,}")
    c2.metric("Columns", f"{df.shape[1]:,}")
    c3.metric("Duplicate records", f"{int(df.duplicated().sum()):,}")
    quality = pd.DataFrame({
        "Column": df.columns,
        "Data type": [str(t) for t in df.dtypes],
        "Missing values": [int(v) for v in df.isna().sum().values],
        "Missing %": [round(float(v) / max(len(df), 1) * 100, 2) for v in df.isna().sum().values],
    })
    st.dataframe(quality, use_container_width=True, hide_index=True)


def main():
    st.title("📊 Sales Analytics Dashboard")
    st.caption("Upload, validate, clean, explore, and visualize your sales data.")
    uploaded = st.sidebar.file_uploader("Upload your dataset", type=["csv", "xlsx", "json"])
    if uploaded is None:
        st.info("Upload a CSV, Excel (.xlsx), or JSON file from the sidebar to get started.")
        st.markdown("**Expected sales fields for all five KPIs:** `Sales`, `Profit`, `Order ID`, and `Quantity`. Filters and charts adapt to available columns.")
        st.stop()

    try:
        raw = load_data(uploaded)
        if raw.empty:
            st.warning("The uploaded file contains no rows.")
            st.stop()
        if raw.columns.duplicated().any():
            st.warning("Duplicate column names detected. Rename them before analysis to avoid ambiguity.")
        st.success(f"Loaded {uploaded.name} successfully.")
    except Exception as exc:
        st.error(f"Could not read this file: {exc}")
        st.stop()

    with st.expander("1 · Data validation — uploaded data", expanded=True):
        show_quality(raw, "Raw data quality")
        st.dataframe(raw.head(10), use_container_width=True)

    st.sidebar.header("2 · Preprocessing")
    fill_method = st.sidebar.selectbox("Missing-value strategy", [
        "Keep missing values", "Fill numeric with median / text with mode", "Drop rows with missing values"
    ])
    remove_duplicates = st.sidebar.checkbox("Remove duplicate records", value=True)
    data = preprocess_data(raw, fill_method, remove_duplicates)
    if data.empty:
        st.error("Preprocessing removed all rows. Choose a less aggressive missing-value strategy.")
        st.stop()

    with st.expander("Preprocessed data quality", expanded=False):
        show_quality(data, "Cleaned data quality")
        st.dataframe(data.head(10), use_container_width=True)

    st.sidebar.header("3 · Interactive filters")
    filtered = data.copy()
    filter_columns = [c for c in ["Region", "Category", "Segment", "Ship Mode", "State"] if c in filtered.columns]
    for col in filter_columns[:5]:
        options = sorted(filtered[col].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect(col, options, default=options, key=f"filter_{col}")
        if selected:
            filtered = filtered[filtered[col].astype(str).isin(selected)]
        else:
            filtered = filtered.iloc[0:0]

    date_col = "Order Date" if "Order Date" in filtered.columns else next(
        (c for c in filtered.columns if "date" in c.lower() and pd.api.types.is_datetime64_any_dtype(filtered[c])), None
    )
    if date_col:
        valid_dates = filtered[date_col].dropna()
        if not valid_dates.empty:
            date_range = st.sidebar.date_input(
                f"{date_col} range", value=(valid_dates.min().date(), valid_dates.max().date()),
                min_value=valid_dates.min().date(), max_value=valid_dates.max().date()
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
                filtered = filtered[filtered[date_col].between(start, end)]

    required = ["Sales", "Profit", "Quantity", "Order ID"]
    missing_required = [c for c in required if c not in filtered.columns]
    if missing_required:
        st.error("Cannot calculate all requested KPIs. Missing columns: " + ", ".join(missing_required))
        st.caption("Rename your source columns to Sales, Profit, Quantity, and Order ID, then upload again.")
        st.stop()

    st.subheader("4 · Key performance indicators")
    total_sales = pd.to_numeric(filtered["Sales"], errors="coerce").sum()
    total_profit = pd.to_numeric(filtered["Profit"], errors="coerce").sum()
    total_orders = filtered["Order ID"].nunique(dropna=True)
    total_quantity = pd.to_numeric(filtered["Quantity"], errors="coerce").sum()
    margin = (total_profit / total_sales * 100) if total_sales else 0
    kpis = st.columns(5)
    kpis[0].metric("Total Sales", money(total_sales))
    kpis[1].metric("Total Profit", money(total_profit))
    kpis[2].metric("Total Orders", f"{total_orders:,}")
    kpis[3].metric("Total Quantity Sold", f"{total_quantity:,.0f}")
    kpis[4].metric("Profit Margin", f"{margin:.2f}%")
    st.caption(f"Showing {len(filtered):,} of {len(data):,} preprocessed rows after filters.")

    st.subheader("5 · Interactive visualizations")
    if filtered.empty:
        st.warning("No records match the selected filters. Adjust the filters in the sidebar.")
    else:
        chart1, chart2 = st.columns(2)
        if "Category" in filtered.columns:
            cat = filtered.groupby("Category", dropna=False, as_index=False)[["Sales", "Profit"]].sum()
            fig = px.bar(cat, x="Category", y=["Sales", "Profit"], barmode="group", title="Sales and profit by category")
            chart1.plotly_chart(fig, use_container_width=True)
        elif "Region" in filtered.columns:
            reg = filtered.groupby("Region", as_index=False)[["Sales", "Profit"]].sum()
            chart1.plotly_chart(px.bar(reg, x="Region", y=["Sales", "Profit"], barmode="group", title="Sales and profit by region"), use_container_width=True)
        else:
            chart1.info("Add a Category or Region column for the category comparison chart.")

        if date_col:
            trend = filtered.dropna(subset=[date_col]).groupby(pd.Grouper(key=date_col, freq="MS"), as_index=False)[["Sales", "Profit"]].sum()
            chart2.plotly_chart(px.line(trend, x=date_col, y=["Sales", "Profit"], markers=True, title="Monthly sales and profit trend"), use_container_width=True)
        elif "Sub-Category" in filtered.columns:
            sub = filtered.groupby("Sub-Category", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False).head(12)
            chart2.plotly_chart(px.bar(sub, x="Sub-Category", y="Sales", title="Top sub-categories by sales"), use_container_width=True)
        else:
            chart2.info("Add a date or Sub-Category column for a trend chart.")

        if "Region" in filtered.columns:
            region_data = filtered.groupby("Region", as_index=False)["Profit"].sum()
            fig3 = px.pie(region_data, names="Region", values="Profit", title="Profit contribution by region", hole=0.35)
        elif "Segment" in filtered.columns:
            segment_data = filtered.groupby("Segment", as_index=False)["Sales"].sum()
            fig3 = px.pie(segment_data, names="Segment", values="Sales", title="Sales contribution by segment", hole=0.35)
        else:
            fig3 = px.histogram(filtered, x="Sales", title="Sales distribution")
        st.plotly_chart(fig3, use_container_width=True)

    with st.expander("6 · Statistical summary", expanded=False):
        summary = numeric_summary(filtered)
        if summary.empty:
            st.info("No numeric columns are available for statistical summaries.")
        else:
            st.dataframe(summary, use_container_width=True)

    st.subheader("7 · Export cleaned and filtered data")
    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data as CSV", csv_bytes, "sales_data_cleaned.csv", "text/csv")


if __name__ == "__main__":
    main()
