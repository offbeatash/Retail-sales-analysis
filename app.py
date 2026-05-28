import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import hmac
import io
import secrets
import zipfile
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor


def get_connection():
    return sqlite3.connect('sales_database.db')


CRYSTAL_REPORT_DATASETS = {
    "executive_summary.csv": """
        SELECT
            COUNT(*) AS Total_Orders,
            ROUND(SUM(Revenue), 2) AS Total_Revenue,
            ROUND(SUM(Profit), 2) AS Total_Profit,
            ROUND(AVG(Revenue), 2) AS Average_Order_Value,
            ROUND(AVG(Profit_Margin_Pct), 2) AS Average_Profit_Margin
        FROM sales_data
    """,
    "region_summary.csv": """
        SELECT
            Region,
            COUNT(*) AS Orders,
            ROUND(SUM(Revenue), 2) AS Total_Revenue,
            ROUND(SUM(Profit), 2) AS Total_Profit,
            ROUND(AVG(Profit_Margin_Pct), 2) AS Average_Profit_Margin
        FROM sales_data
        GROUP BY Region
        ORDER BY Total_Revenue DESC
    """,
    "monthly_summary.csv": """
        SELECT
            SUBSTR(Date, 1, 7) AS Month,
            COUNT(*) AS Orders,
            ROUND(SUM(Revenue), 2) AS Total_Revenue,
            ROUND(SUM(Profit), 2) AS Total_Profit
        FROM sales_data
        GROUP BY Month
        ORDER BY Month
    """,
    "category_summary.csv": """
        SELECT
            Category,
            COUNT(*) AS Orders,
            ROUND(SUM(Revenue), 2) AS Total_Revenue,
            ROUND(SUM(Profit), 2) AS Total_Profit
        FROM sales_data
        GROUP BY Category
        ORDER BY Total_Revenue DESC
    """,
    "top_products.csv": """
        SELECT
            Product_Name,
            Brand,
            Category,
            COUNT(*) AS Orders,
            ROUND(SUM(Revenue), 2) AS Total_Revenue,
            ROUND(SUM(Profit), 2) AS Total_Profit
        FROM sales_data
        GROUP BY Product_Name, Brand, Category
        ORDER BY Total_Revenue DESC
        LIMIT 20
    """,
    "channel_payment_summary.csv": """
        SELECT
            Sales_Channel,
            Payment_Method,
            COUNT(*) AS Orders,
            ROUND(SUM(Revenue), 2) AS Total_Revenue,
            ROUND(SUM(Profit), 2) AS Total_Profit
        FROM sales_data
        GROUP BY Sales_Channel, Payment_Method
        ORDER BY Total_Revenue DESC
    """,
    "city_summary.csv": """
        SELECT
            City,
            Region,
            COUNT(*) AS Orders,
            ROUND(SUM(Revenue), 2) AS Total_Revenue,
            ROUND(SUM(Profit), 2) AS Total_Profit
        FROM sales_data
        GROUP BY City, Region
        ORDER BY Total_Revenue DESC
    """,
    "raw_sales_sample.csv": """
        SELECT
            Order_ID,
            Date,
            Product_Name,
            Category,
            Brand,
            Quantity,
            Revenue,
            Profit,
            City,
            Region,
            Sales_Channel,
            Payment_Method
        FROM sales_data
        ORDER BY Date DESC
        LIMIT 500
    """,
}


CRYSTAL_REPORT_SQL = """
-- Optional SQLite views for SAP Crystal Reports via SQLite ODBC.

CREATE VIEW IF NOT EXISTS crystal_region_summary AS
SELECT
    Region,
    COUNT(*) AS Orders,
    ROUND(SUM(Revenue), 2) AS Total_Revenue,
    ROUND(SUM(Profit), 2) AS Total_Profit,
    ROUND(AVG(Profit_Margin_Pct), 2) AS Average_Profit_Margin
FROM sales_data
GROUP BY Region;

CREATE VIEW IF NOT EXISTS crystal_monthly_summary AS
SELECT
    SUBSTR(Date, 1, 7) AS Month,
    COUNT(*) AS Orders,
    ROUND(SUM(Revenue), 2) AS Total_Revenue,
    ROUND(SUM(Profit), 2) AS Total_Profit
FROM sales_data
GROUP BY Month;

CREATE VIEW IF NOT EXISTS crystal_category_summary AS
SELECT
    Category,
    COUNT(*) AS Orders,
    ROUND(SUM(Revenue), 2) AS Total_Revenue,
    ROUND(SUM(Profit), 2) AS Total_Profit
FROM sales_data
GROUP BY Category;

"""


CRYSTAL_REPORT_GUIDE = """
# Crystal Report Setup for Retail Sales Analysis

This ZIP was generated from the Streamlit admin dashboard.

## Files

- `pdf/*.pdf`: generated PDF report sections
- `crystal_report_queries.sql`: optional SQLite views for direct ODBC reporting
- `schema.txt`: source table structure

## PDF Reports Included

1. Executive Summary
2. Regional Performance
3. Monthly Performance
4. Category Performance
5. Top Products
6. Channel and Payment Insights
7. City Summary
8. Raw Sales Sample

## Creating a native .rpt file

SAP Crystal Reports must be installed to create a native `.rpt` file. Open
Crystal Reports, create a Standard Report, connect to `sales_database.db`
through SQLite ODBC, or use `crystal_report_queries.sql` to create report
views, then save as:
`Retail_Sales_Analysis.rpt`.
"""


def init_admin_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt),
        120000
    ).hex()
    return salt, password_hash


def create_admin(username, password):
    username = username.strip().lower()
    salt, password_hash = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO admin_users (username, password_hash, salt)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, salt)
        )
        conn.commit()
        return True, "Admin account created. Please log in."
    except sqlite3.IntegrityError:
        return False, "This username already exists."
    finally:
        conn.close()


def verify_admin(username, password):
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, password_hash, salt FROM admin_users WHERE username = ?",
        (username,)
    )
    admin = cursor.fetchone()
    conn.close()

    if not admin:
        return False

    _, stored_hash, salt = admin
    _, password_hash = hash_password(password, salt)
    return hmac.compare_digest(password_hash, stored_hash)


def admin_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM admin_users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def show_auth_page():
    st.subheader("Admin Access")
    st.caption("Register an admin account or log in to view the dashboard.")

    if admin_count() == 0:
        st.info("No admin account exists yet. Create the first admin account to continue.")

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("admin_login_form"):
            username = st.text_input("Admin Username", key="login_username")
            password = st.text_input("Admin Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")

        if submitted:
            if verify_admin(username, password):
                st.session_state["admin_logged_in"] = True
                st.session_state["admin_username"] = username.strip().lower()
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid admin username or password.")

    with register_tab:
        with st.form("admin_register_form"):
            new_username = st.text_input("New Admin Username", key="register_username")
            new_password = st.text_input("New Admin Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm Admin Password", type="password")
            registered = st.form_submit_button("Create Admin")

        if registered:
            if len(new_username.strip()) < 3:
                st.error("Username must be at least 3 characters.")
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                created, message = create_admin(new_username, new_password)
                if created:
                    st.success(message)
                else:
                    st.error(message)


init_admin_table()

if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if not st.session_state["admin_logged_in"]:
    show_auth_page()
    st.stop()

with st.sidebar:
    st.success(f"Logged in as {st.session_state['admin_username']}")
    if st.button("Logout"):
        st.session_state["admin_logged_in"] = False
        st.session_state.pop("admin_username", None)
        st.rerun()


@st.cache_data
def load_data(query):
    conn = get_connection()
    data = pd.read_sql_query(query, conn)
    conn.close()
    return data


def pdf_filename(csv_filename):
    return csv_filename.replace(".csv", ".pdf")


def clean_pdf_value(value, max_length=38):
    if pd.isna(value):
        return ""

    text = str(value)
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


def dataframe_to_pdf(title, dataset):
    pdf_buffer = io.BytesIO()
    rows_per_page = 28 if len(dataset.columns) <= 6 else 18
    total_rows = max(len(dataset), 1)

    with PdfPages(pdf_buffer) as pdf:
        for start in range(0, total_rows, rows_per_page):
            if dataset.empty:
                page_data = pd.DataFrame({"Message": ["No records found."]})
                page_number = 1
                total_pages = 1
            else:
                page_data = dataset.iloc[start:start + rows_per_page].copy()
                page_number = (start // rows_per_page) + 1
                total_pages = ((len(dataset) - 1) // rows_per_page) + 1

            display_data = page_data.applymap(clean_pdf_value)
            figure = Figure(figsize=(11.69, 8.27))
            axis = figure.add_subplot(111)
            axis.axis("off")

            figure.text(0.04, 0.96, title, fontsize=18, weight="bold", color="#1c2c44")
            figure.text(
                0.04,
                0.925,
                f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | Page {page_number} of {total_pages}",
                fontsize=9,
                color="#64748b"
            )

            table = axis.table(
                cellText=display_data.values,
                colLabels=display_data.columns,
                cellLoc="left",
                colLoc="left",
                bbox=[0.02, 0.02, 0.96, 0.84],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(6 if len(display_data.columns) > 8 else 8)
            table.scale(1, 1.25)

            for (row, _), cell in table.get_celld().items():
                if row == 0:
                    cell.set_facecolor("#1c2c44")
                    cell.set_text_props(color="white", weight="bold")
                else:
                    cell.set_facecolor("#f8fafc" if row % 2 == 0 else "white")

            pdf.savefig(figure)

            if dataset.empty:
                break

    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


@st.cache_data
def build_crystal_report_package():
    zip_buffer = io.BytesIO()

    with sqlite3.connect('sales_database.db') as conn:
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as report_zip:
            for filename, query in CRYSTAL_REPORT_DATASETS.items():
                dataset = pd.read_sql_query(query, conn)
                title = filename.replace(".csv", "").replace("_", " ").title()
                report_zip.writestr(f"pdf/{pdf_filename(filename)}", dataframe_to_pdf(title, dataset))

            schema_rows = conn.execute("PRAGMA table_info(sales_data)").fetchall()
            schema_lines = ["sales_data schema", "=================", ""]
            for _, name, column_type, not_null, default, primary_key in schema_rows:
                schema_lines.append(
                    f"{name}: {column_type or 'TEXT'}"
                    f"{' NOT NULL' if not_null else ''}"
                    f"{' PRIMARY KEY' if primary_key else ''}"
                    f"{f' DEFAULT {default}' if default else ''}"
                )

            report_zip.writestr("schema.txt", "\n".join(schema_lines))
            report_zip.writestr("crystal_report_queries.sql", CRYSTAL_REPORT_SQL.strip() + "\n")
            report_zip.writestr("README_Crystal_Report_Setup.md", CRYSTAL_REPORT_GUIDE.strip() + "\n")

    zip_buffer.seek(0)
    return zip_buffer.getvalue()

@st.cache_data
def get_tree_feature_importance():
    sales_data = load_data("""
        SELECT
            Date,
            Product_Name,
            Category,
            Brand,
            Unit_Price,
            Discount_Percent,
            Selling_Price,
            Quantity,
            Revenue,
            City,
            Region,
            Sales_Channel,
            Payment_Method,
            Return_Flag,
            Customer_Segment,
            Festival_Season
        FROM sales_data
    """)

    sales_data['Date'] = pd.to_datetime(sales_data['Date'], errors='coerce')
    required_cols = [
        'Date', 'Product_Name', 'Category', 'Brand', 'Unit_Price',
        'Discount_Percent', 'Selling_Price', 'Quantity', 'Revenue', 'City',
        'Region', 'Sales_Channel', 'Payment_Method', 'Return_Flag',
        'Customer_Segment', 'Festival_Season'
    ]
    sales_data = sales_data.dropna(subset=required_cols)

    if len(sales_data) < 50:
        return pd.DataFrame()

    sales_data['MonthNum'] = sales_data['Date'].dt.month
    sales_data['DayOfWeek'] = sales_data['Date'].dt.dayofweek
    sales_data['DayOfMonth'] = sales_data['Date'].dt.day
    sales_data['WeekOfYear'] = sales_data['Date'].dt.isocalendar().week.astype(int)
    sales_data['IsWeekend'] = (sales_data['DayOfWeek'] >= 5).astype(int)
    sales_data['Festival_Season'] = sales_data['Festival_Season'].astype(int)
    sales_data['Return_Flag_Num'] = (sales_data['Return_Flag'] == 'Yes').astype(int)

    numeric_features = [
        'Unit_Price', 'Discount_Percent', 'Selling_Price', 'Quantity',
        'MonthNum', 'DayOfWeek', 'DayOfMonth', 'WeekOfYear', 'IsWeekend',
        'Festival_Season', 'Return_Flag_Num'
    ]
    categorical_features = [
        'Product_Name', 'Category', 'Brand', 'City', 'Region',
        'Sales_Channel', 'Payment_Method', 'Customer_Segment'
    ]

    X = pd.get_dummies(
        sales_data[numeric_features + categorical_features],
        columns=categorical_features,
        dtype=int
    )
    y = sales_data['Revenue']

    models = {
        'Random Forest': RandomForestRegressor(
            n_estimators=120,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=1
        ),
        'Gradient Boosting': GradientBoostingRegressor(
            n_estimators=120,
            random_state=42
        )
    }

    def feature_group(encoded_feature):
        for categorical_feature in categorical_features:
            if encoded_feature.startswith(f'{categorical_feature}_'):
                return categorical_feature
        return encoded_feature

    grouped_importances = {}
    groups = pd.Series([feature_group(col) for col in X.columns], index=X.columns)

    for model_name, model in models.items():
        model.fit(X, y)
        importances = pd.Series(model.feature_importances_, index=X.columns)
        importances = importances / importances.sum()
        grouped_importances[model_name] = importances.groupby(groups).sum()

    importance_df = pd.DataFrame(grouped_importances).fillna(0)
    importance_df['Average_Importance'] = importance_df.mean(axis=1)
    importance_df = (
        importance_df
        .sort_values('Average_Importance', ascending=False)
        .head(12)
        .reset_index()
        .rename(columns={'index': 'Feature'})
    )
    return importance_df

st.subheader("Executive Summary")
kpi_data = load_data("""
    SELECT 
        COUNT(*) as Total_Orders,
        SUM(Revenue) as Total_Revenue,
        SUM(Profit) as Total_Profit
    FROM sales_data
""")

total_orders = kpi_data['Total_Orders'][0]
total_revenue = kpi_data['Total_Revenue'][0]
total_profit = kpi_data['Total_Profit'][0]

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(label="Total Orders", value=f"{total_orders:,}")
kpi2.metric(label="Total Revenue", value=f"₹{total_revenue:,.2f}")
kpi3.metric(label="Total Profit", value=f"₹{total_profit:,.2f}")
st.divider()

st.subheader("Sales by Region (Live from SQLite!)")
sql_query = """
    SELECT 
        Region, 
        SUM(Revenue) as Total_Revenue,
        SUM(Profit) as Total_Profit
    FROM sales_data 
    GROUP BY Region
    ORDER BY Total_Revenue DESC
"""
df_region = load_data(sql_query)

col1, col2 = st.columns(2)
with col1:
    st.dataframe(df_region, width='stretch')
with col2:
    st.bar_chart(data=df_region, x='Region', y='Total_Revenue')
st.divider()

st.subheader("Monthly Performance (Satisfactory vs. Below Average)")
monthly_data = load_data("""
    SELECT 
        SUBSTR(Date, 1, 7) as Month, 
        SUM(Revenue) as Total_Revenue
    FROM sales_data 
    GROUP BY Month
    ORDER BY Month
""")

target_avg = 32190780
monthly_data['Status'] = monthly_data['Total_Revenue'].apply(lambda x: 'Satisfactory' if x >= target_avg else 'Below Average')

import altair as alt

color_scale = alt.Scale(
    domain=['Satisfactory', 'Below Average'],
    range=['#2ecc71', '#e74c3c'] 
)

chart = alt.Chart(monthly_data).mark_bar().encode(
    x='Month',
    y='Total_Revenue',
    color=alt.Color('Status:N', scale=color_scale),
    tooltip=['Month', 'Total_Revenue', 'Status']
).properties(
    width='container' 
)

st.altair_chart(chart, width='stretch')

st.divider()

st.subheader("Tree-Based Feature Importance")
with st.spinner("Training tree models on current sales data..."):
    feature_importance = get_tree_feature_importance()

if feature_importance.empty:
    st.warning("Not enough complete records are available to calculate feature importance.")
else:
    top_feature = feature_importance.iloc[0]
    fi_chart_data = feature_importance.sort_values('Average_Importance', ascending=True)

    fi_col1, fi_col2 = st.columns([2, 1])
    with fi_col1:
        fi_chart = alt.Chart(fi_chart_data).mark_bar(color='#4c78a8').encode(
            x=alt.X('Average_Importance:Q', title='Average Importance'),
            y=alt.Y('Feature:N', title='Feature', sort=None),
            tooltip=[
                alt.Tooltip('Feature:N'),
                alt.Tooltip('Average_Importance:Q', format='.2%'),
                alt.Tooltip('Random Forest:Q', format='.2%'),
                alt.Tooltip('Gradient Boosting:Q', format='.2%')
            ]
        ).properties(height=360)
        st.altair_chart(fi_chart, width='stretch')

    with fi_col2:
        st.metric(
            label="Top Revenue Driver",
            value=top_feature['Feature'],
            delta=f"{top_feature['Average_Importance']:.1%} avg importance"
        )
        st.dataframe(
            feature_importance.style.format({
                'Average_Importance': '{:.2%}',
                'Random Forest': '{:.2%}',
                'Gradient Boosting': '{:.2%}'
            }),
            width='stretch',
            hide_index=True
        )

st.divider()

st.subheader("➕ Add New Sales Record")
with st.form("add_new_row_form"):
    form_col1, form_col2 = st.columns(2)
    
    with form_col1:
        new_date = st.date_input("Date")
        new_category = st.selectbox("Category", ["Smartphones", "Laptops", "Audio", "Cameras", "Accessories", "Other"])
        new_product = st.text_input("Product Name")
        new_brand = st.text_input("Brand")
        
    with form_col2:
        new_region = st.selectbox("Region", ["North", "South", "East", "West"])
        new_revenue = st.number_input("Revenue", min_value=0.0, format="%.2f")
        new_profit = st.number_input("Profit", format="%.2f")
        
    submitted = st.form_submit_button("Save to Database")

if submitted:
    conn = sqlite3.connect('sales_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sales_data (Date, Category, Product_Name, Brand, Region, Revenue, Profit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (new_date, new_category, new_product, new_brand, new_region, new_revenue, new_profit))
    
    conn.commit()
    conn.close()
    st.cache_data.clear()
    st.success(f"Successfully added {new_product} to the database! Refreshing charts...")

st.divider()

st.subheader("Explore Raw Data")
categories = load_data("SELECT DISTINCT Category FROM sales_data")['Category'].tolist()
selected_category = st.selectbox("Select a Product Category:", categories)

filtered_query = f"SELECT Date, Product_Name, Brand, Revenue FROM sales_data WHERE Category = '{selected_category}' LIMIT 100"
df_filtered = load_data(filtered_query)

st.write(f"Showing top 100 sales for: **{selected_category}**")
st.dataframe(df_filtered, width='stretch')
st.divider()

st.subheader("Crystal Report Generator")
st.write("Generate PDF report files from the current SQLite sales database.")

crystal_col1, crystal_col2, crystal_col3 = st.columns(3)
crystal_col1.metric("PDF Reports", len(CRYSTAL_REPORT_DATASETS))
crystal_col2.metric("Source Table", "sales_data")
crystal_col3.metric("Format", "PDF ZIP")

crystal_report_zip = build_crystal_report_package()
st.download_button(
    label="Download Crystal Report Package",
    data=crystal_report_zip,
    file_name="Retail_Sales_Crystal_Report_Package.zip",
    mime="application/zip"
)

with st.expander("What is included?"):
    st.write(
        """
        The ZIP includes PDF report files for executive, region, monthly,
        category, product, city, channel, and raw-sales reporting. It also
        includes SQL view definitions and a setup guide for creating a native
        `.rpt` file in SAP Crystal Reports if needed.
        """
    )

st.divider()

st.subheader("🔍 Quick Insights")
analysis_option = st.selectbox(
    "What analysis do you need?",
    [
        "Select an option...", 
        "Highest Selling Product", 
        "Best Performing Month", 
        "Predicted Sales (Next Month)"
    ]
)

if analysis_option == "Highest Selling Product":
    best_product = load_data("""
        SELECT Product_Name, Brand, SUM(Revenue) as Total_Rev 
        FROM sales_data 
        GROUP BY Product_Name 
        ORDER BY Total_Rev DESC LIMIT 1
    """)
    st.success(f"🏆 The Highest Selling Product is the **{best_product['Product_Name'][0]}** ({best_product['Brand'][0]}) with **₹{best_product['Total_Rev'][0]:,.2f}** in revenue.")

elif analysis_option == "Best Performing Month":
    best_month = load_data("""
        SELECT SUBSTR(Date, 1, 7) as Month, SUM(Revenue) as Total_Rev 
        FROM sales_data 
        GROUP BY Month 
        ORDER BY Total_Rev DESC LIMIT 1
    """)
    st.success(f"📅 Your Best Month was **{best_month['Month'][0]}**, bringing in **₹{best_month['Total_Rev'][0]:,.2f}**.")

elif analysis_option == "Predicted Sales (Next Month)":
    avg_monthly = load_data("""
        WITH MonthlyData AS (
            SELECT SUBSTR(Date, 1, 7) as Month, SUM(Revenue) as Total_Rev 
            FROM sales_data GROUP BY Month
        )
        SELECT AVG(Total_Rev) as Avg_Rev FROM MonthlyData
    """)
    prediction = avg_monthly['Avg_Rev'][0]
    
    st.info("🤖 **AI Prediction:** Based on historical run-rate, next month's baseline revenue is projected to be:")
    st.metric(label="Forecasted Revenue", value=f"₹{prediction:,.2f}")
