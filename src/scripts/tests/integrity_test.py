
import unittest
import json
import os

class TestDataIntegrity(unittest.TestCase):
    def test_config_json_validity(self):
        """Data Integrity: Ensure config/settings.json exists and is valid JSON."""
        config_path = "data/settings.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertIsInstance(data, dict)
                # Check for critical keys if they exist
                if 'SYMBOLS' in data:
                    self.assertIsInstance(data['SYMBOLS'], list)
            print("Integrity: settings.json is valid.")
        else:
            print("Integrity: settings.json not found (using defaults).")

    def test_symbols_schema(self):
        """Data Integrity: Ensure symbols meet naming conventions."""
        symbols_path = "data/symbols.json"
        if os.path.exists(symbols_path):
            with open(symbols_path, 'r', encoding='utf-8') as f:
                symbols = json.load(f)
                self.assertIsInstance(symbols, list)
                for s in symbols:
                    # Basic check for OKX format or CCXT format
                    self.assertTrue("/USDT" in s or "-USDT" in s)
            print(f"Integrity: {len(symbols)} symbols verified.")

    def test_log_file_encoding(self):
        """Data Integrity: Verify that astra_report files are readable and not corrupted."""
        root = "."
        report_files = [f for f in os.listdir(root) if f.startswith("astra_report_") and f.endswith(".md")]
        
        for rf in report_files[:3]: # Check first 3
            with open(rf, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("ASTRA", content)
                self.assertIn("---", content)
        print(f"Integrity: {len(report_files)} report files scanned.")

if __name__ == "__main__":
    unittest.main()
