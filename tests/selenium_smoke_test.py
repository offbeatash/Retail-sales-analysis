import argparse
import contextlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"


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


def run_smoke_test(url):
    driver = webdriver.Chrome(options=chrome_options())
    try:
        driver.get(url)

        required_text = [
            "Executive Summary",
            "Total Orders",
            "Total Revenue",
            "Sales by Region",
            "Monthly Performance",
            "Tree-Based Feature Importance",
            "Add New Sales Record",
            "Explore Raw Data",
            "Quick Insights",
        ]

        for text in required_text:
            assert_text_present(driver, text)

        metrics = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stMetric']")
        if len(metrics) < 3:
            raise AssertionError(f"Expected at least 3 KPI metrics, found {len(metrics)}")

        dataframes = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stDataFrame']")
        if not dataframes:
            raise AssertionError("Expected at least one rendered dataframe")

        print("PASS: Streamlit dashboard loaded and key sections rendered.")
        print(f"PASS: Found {len(metrics)} KPI metrics and {len(dataframes)} dataframe component(s).")
    finally:
        driver.quit()


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
