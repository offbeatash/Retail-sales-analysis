import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Electronics Sales Dashboard", layout="wide")
st.title("📊 Electronics Sales Analytics")

@st.cache_data
def load_data(query):
    conn = sqlite3.connect('sales_database.db')
    data = pd.read_sql_query(query, conn)
    conn.close()
    return data

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

st.altair_chart(chart, use_container_width=True)

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