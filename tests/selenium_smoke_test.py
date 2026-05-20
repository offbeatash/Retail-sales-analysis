import argparse
import contextlib
import os
import sqlite3
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"
DB_FILE = ROOT / "sales_database.db"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_http(url, timeout=90):
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            with urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    raise RuntimeError(f"Streamlit did not become ready at {url}: {last_error}")


def start_streamlit(port):
    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP_FILE),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if chrome_path.exists():
        options.binary_location = str(chrome_path)

    return options


def assert_text_present(driver, text):
    WebDriverWait(driver, 90).until(
        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text)
    )


def page_text(driver):
    return driver.find_element(By.TAG_NAME, "body").text


def assert_body_contains(driver, expected_text, timeout=30):
    WebDriverWait(driver, timeout).until(
        lambda current_driver: expected_text in page_text(current_driver)
    )


def click_button(driver, text, timeout=30):
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//button[not(@role='tab')][.//*[normalize-space()={xpath_literal(text)}] or normalize-space()={xpath_literal(text)}]",
            )
        )
    )
    element.click()


def click_tab(driver, text, timeout=30):
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f"//*[@role='tab'][.//*[normalize-space()={xpath_literal(text)}] or normalize-space()={xpath_literal(text)}]",
            )
        )
    )
    element.click()


def fill_text_input(driver, label, value, timeout=30):
    input_xpath = (
        f"//div[@data-testid='stTextInput'][.//*[normalize-space()={xpath_literal(label)}]]"
        "//input"
    )
    input_element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, input_xpath))
    )
    input_element.clear()
    input_element.send_keys(value)


def delete_admin(username):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM admin_users WHERE username = ?", (username,))
        conn.commit()


def register_and_login_admin(driver):
    username = f"selenium_admin_{uuid.uuid4().hex[:8]}"
    password = "TestPass123!"

    assert_body_contains(driver, "Admin Access")
    click_tab(driver, "Register")
    fill_text_input(driver, "New Admin Username", username)
    fill_text_input(driver, "New Admin Password", password)
    fill_text_input(driver, "Confirm Admin Password", password)
    click_button(driver, "Create Admin")
    assert_body_contains(driver, "Admin account created")

    click_tab(driver, "Login")
    fill_text_input(driver, "Admin Username", username)
    fill_text_input(driver, "Admin Password", password)
    click_button(driver, "Login")
    assert_body_contains(driver, "Executive Summary", timeout=90)

    return username


def fetch_one(query):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        return dict(conn.execute(query).fetchone())


def dashboard_expectations():
    kpis = fetch_one(
        """
        SELECT
            COUNT(*) AS total_orders,
            SUM(Revenue) AS total_revenue,
            SUM(Profit) AS total_profit
        FROM sales_data
        """
    )
    top_product = fetch_one(
        """
        SELECT Product_Name, Brand, SUM(Revenue) AS total_revenue
        FROM sales_data
        GROUP BY Product_Name
        ORDER BY total_revenue DESC
        LIMIT 1
        """
    )
    best_month = fetch_one(
        """
        SELECT SUBSTR(Date, 1, 7) AS month, SUM(Revenue) AS total_revenue
        FROM sales_data
        GROUP BY month
        ORDER BY total_revenue DESC
        LIMIT 1
        """
    )
    test_category = fetch_one(
        """
        SELECT Category AS category
        FROM sales_data
        GROUP BY Category
        ORDER BY COUNT(*) DESC, Category
        LIMIT 1
        """
    )
    return {
        "kpis": kpis,
        "top_product": top_product,
        "best_month": best_month,
        "test_category": test_category["category"],
    }


def select_streamlit_option(driver, label, option):
    label_xpath = (
        f"//div[@data-testid='stSelectbox'][.//*[normalize-space()={xpath_literal(label)}]]"
    )
    selectbox = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, label_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selectbox)
    time.sleep(0.2)

    combobox = selectbox.find_element(By.XPATH, ".//*[@role='combobox']")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(combobox))
    combobox.click()

    option_xpath = f"//*[@role='option'][.//*[normalize-space()={xpath_literal(option)}] or normalize-space()={xpath_literal(option)}]"
    option_element = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, option_xpath))
    )
    option_element.click()


def xpath_literal(value):
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ', "\'", '.join(f"'{part}'" for part in parts) + ")"


def run_smoke_test(url):
    expectations = dashboard_expectations()
    test_admin_username = None
    driver = webdriver.Chrome(options=chrome_options())
    try:
        driver.get(url)
        test_admin_username = register_and_login_admin(driver)

        required_text = [
            "Executive Summary",
            "Total Orders",
            "Total Revenue",
            "Sales by Region",
            "Monthly Performance",
            "Tree-Based Feature Importance",
            "Add New Sales Record",
            "Explore Raw Data",
            "Crystal Report Generator",
            "Download Crystal Report Package",
            "PDF Reports",
            "PDF ZIP",
            "Quick Insights",
        ]

        for text in required_text:
            assert_text_present(driver, text)

        kpis = expectations["kpis"]
        expected_values = [
            f"{kpis['total_orders']:,}",
            f"{kpis['total_revenue']:,.2f}",
            f"{kpis['total_profit']:,.2f}",
        ]
        for value in expected_values:
            assert_body_contains(driver, value)

        metrics = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stMetric']")
        if len(metrics) < 4:
            raise AssertionError(f"Expected at least 4 KPI metrics, found {len(metrics)}")

        dataframes = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stDataFrame']")
        if len(dataframes) < 3:
            raise AssertionError(f"Expected at least 3 rendered dataframes, found {len(dataframes)}")

        charts = driver.find_elements(
            By.CSS_SELECTOR,
            "[data-testid='stVegaLiteChart'], [data-testid='stArrowVegaLiteChart']",
        )
        if len(charts) < 3:
            raise AssertionError(f"Expected at least 3 rendered charts, found {len(charts)}")

        selected_category = expectations["test_category"]
        select_streamlit_option(driver, "Select a Product Category:", selected_category)
        assert_body_contains(driver, f"Showing top 100 sales for: {selected_category}")

        top_product = expectations["top_product"]
        select_streamlit_option(driver, "What analysis do you need?", "Highest Selling Product")
        assert_body_contains(driver, top_product["Product_Name"])
        assert_body_contains(driver, top_product["Brand"])
        assert_body_contains(driver, f"{top_product['total_revenue']:,.2f}")

        best_month = expectations["best_month"]
        select_streamlit_option(driver, "What analysis do you need?", "Best Performing Month")
        assert_body_contains(driver, best_month["month"])
        assert_body_contains(driver, f"{best_month['total_revenue']:,.2f}")

        print("PASS: Admin registration and login worked.")
        print("PASS: Streamlit dashboard loaded and key sections rendered.")
        print("PASS: KPI values match the SQLite database totals.")
        print(f"PASS: Found {len(metrics)} KPI metrics and {len(dataframes)} dataframe component(s).")
        print(f"PASS: Found {len(charts)} chart component(s).")
        print(f"PASS: Category filter rendered results for {selected_category}.")
        print("PASS: Quick Insights options returned expected database-backed results.")
    finally:
        driver.quit()
        if test_admin_username:
            delete_admin(test_admin_username)


def main():
    parser = argparse.ArgumentParser(description="Run a Selenium smoke test for the Streamlit dashboard.")
    parser.add_argument("--url", help="Use an already-running app URL instead of starting Streamlit.")
    args = parser.parse_args()

    if args.url:
        run_smoke_test(args.url.rstrip("/"))
        return

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    process = start_streamlit(port)

    try:
        wait_for_http(url)
        run_smoke_test(url)
    finally:
        process.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=10)
        if process.poll() is None:
            process.kill()


if __name__ == "__main__":
    main()
