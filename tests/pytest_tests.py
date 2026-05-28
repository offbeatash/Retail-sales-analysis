import os
import re
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"
SELENIUM_TEST_FILE = ROOT / "tests" / "selenium_smoke_test.py"
DB_FILE = ROOT / "sales_database.db"
GITIGNORE_FILE = ROOT / ".gitignore"


class ProjectStandardTests(unittest.TestCase):
    def test_python_files_compile(self):
        files = [APP_FILE, SELENIUM_TEST_FILE, Path(__file__)]
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", *map(str, files)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_database_exists_and_has_sales_table(self):
        self.assertTrue(DB_FILE.exists(), "sales_database.db is required for local testing")

        with sqlite3.connect(DB_FILE) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertIn("sales_data", tables)

            row_count = conn.execute("SELECT COUNT(*) FROM sales_data").fetchone()[0]
            self.assertGreater(row_count, 0)

    def test_sales_data_schema_has_required_columns(self):
        required_columns = {
            "Order_ID",
            "Date",
            "Product_Name",
            "Category",
            "Brand",
            "Quantity",
            "Revenue",
            "Profit",
            "City",
            "Region",
            "Sales_Channel",
            "Payment_Method",
        }

        with sqlite3.connect(DB_FILE) as conn:
            actual_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(sales_data)")
            }

        self.assertTrue(
            required_columns.issubset(actual_columns),
            f"Missing columns: {sorted(required_columns - actual_columns)}",
        )

    def test_dashboard_queries_return_valid_values(self):
        with sqlite3.connect(DB_FILE) as conn:
            total_orders, total_revenue, total_profit = conn.execute(
                """
                SELECT COUNT(*), SUM(Revenue), SUM(Profit)
                FROM sales_data
                """
            ).fetchone()
            top_product = conn.execute(
                """
                SELECT Product_Name
                FROM sales_data
                GROUP BY Product_Name
                ORDER BY SUM(Revenue) DESC
                LIMIT 1
                """
            ).fetchone()

        self.assertGreater(total_orders, 0)
        self.assertGreater(total_revenue, 0)
        self.assertIsNotNone(total_profit)
        self.assertIsNotNone(top_product)

    def test_admin_auth_table_is_securely_structured(self):
        with sqlite3.connect(DB_FILE) as conn:
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(admin_users)")
            }

        self.assertIn("username", columns)
        self.assertIn("password_hash", columns)
        self.assertIn("salt", columns)
        self.assertNotIn("password", columns)

    def test_app_contains_expected_security_and_reporting_features(self):
        app_source = APP_FILE.read_text(encoding="utf-8")

        self.assertIn("hashlib.pbkdf2_hmac", app_source)
        self.assertIn("hmac.compare_digest", app_source)
        self.assertIn("st.download_button", app_source)
        self.assertIn("Crystal Report Generator", app_source)
        self.assertIn("PDF ZIP", app_source)

    def test_gitignore_hides_sensitive_local_files(self):
        self.assertTrue(GITIGNORE_FILE.exists(), ".gitignore is missing")
        gitignore = GITIGNORE_FILE.read_text(encoding="utf-8")

        required_patterns = [
            "*.db",
            "*.csv",
            "*.pbix",
            "reports/",
            ".env",
            "secrets.toml",
            "*.log",
            "__pycache__/",
        ]
        for pattern in required_patterns:
            self.assertIn(pattern, gitignore)

    def test_sensitive_files_are_not_tracked_by_git(self):
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        tracked_files = set(result.stdout.splitlines())
        sensitive_files = {
            "sales_database.db",
            "electronics_sales_2024.csv",
            "Retail_sales_analysis.pbix",
            "streamlit.log",
            "streamlit.err.log",
        }
        self.assertTrue(
            sensitive_files.isdisjoint(tracked_files),
            f"Sensitive files still tracked: {sorted(sensitive_files & tracked_files)}",
        )

    def test_no_common_secret_patterns_in_tracked_text_files(self):
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        secret_patterns = [
            re.compile(r"(api[_-]?key|secret|token|credential|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}", re.IGNORECASE),
            re.compile(r"BEGIN (RSA|OPENSSH|PRIVATE) KEY", re.IGNORECASE),
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        ]
        scanned_extensions = {".py", ".md", ".txt", ".toml", ".json", ".yml", ".yaml", ".gitignore"}
        findings = []

        for relative_path in result.stdout.splitlines():
            path = ROOT / relative_path
            if path.suffix.lower() not in scanned_extensions and path.name != ".gitignore":
                continue
            if not path.exists():
                continue

            content = path.read_text(encoding="utf-8", errors="ignore")
            for line_number, line in enumerate(content.splitlines(), start=1):
                if any(pattern.search(line) for pattern in secret_patterns):
                    findings.append(f"{relative_path}:{line_number}")

        self.assertEqual(findings, [], f"Possible secret references found: {findings}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
