import unittest
import pandas as pd
import io
from utils.data_processing import validate_and_clean_csv

class TestDataProcessing(unittest.TestCase):
    
    def test_valid_csv(self):
        csv_data = """ticker,date,transaction_type,quantity,price
MSFT,2025-06-15,Buy,50,410.00
GOOGL,2025-08-01,Buy,20,145.00
NVDA,2025-09-10,Buy,5,500.00
MSFT,2025-11-20,Buy,30,425.00
NVDA,2026-01-05,Sell,2,650.00
CRM,2026-02-18,Buy,15,280.00
GOOGL,2026-04-10,Sell,10,165.00
ASTS,2026-05-01,Buy,100,8.50"""
        
        file_source = io.StringIO(csv_data)
        df, msg = validate_and_clean_csv(file_source)
        
        self.assertEqual(len(df), 8)
        self.assertEqual(df.loc[0, "ticker"], "MSFT")
        self.assertEqual(df.loc[7, "ticker"], "ASTS")
        self.assertEqual(df.loc[4, "transaction_type"], "Sell")
        self.assertIn("successful", msg)
        
    def test_missing_column(self):
        csv_data = """ticker,date,quantity,price
MSFT,2025-06-15,50,410.00"""
        file_source = io.StringIO(csv_data)
        with self.assertRaises(ValueError) as context:
            validate_and_clean_csv(file_source)
        self.assertIn("missing required columns", str(context.exception))
        
    def test_invalid_transaction_type(self):
        csv_data = """ticker,date,transaction_type,quantity,price
MSFT,2025-06-15,Hold,50,410.00"""
        file_source = io.StringIO(csv_data)
        with self.assertRaises(ValueError) as context:
            validate_and_clean_csv(file_source)
        self.assertIn("Invalid transaction_type value(s)", str(context.exception))
        
    def test_negative_quantity(self):
        csv_data = """ticker,date,transaction_type,quantity,price
MSFT,2025-06-15,Buy,-50,410.00"""
        file_source = io.StringIO(csv_data)
        with self.assertRaises(ValueError) as context:
            validate_and_clean_csv(file_source)
        self.assertIn("Quantity must be greater than zero", str(context.exception))

    def test_negative_balance(self):
        # Selling before buying
        csv_data = """ticker,date,transaction_type,quantity,price
MSFT,2025-06-15,Sell,50,410.00"""
        file_source = io.StringIO(csv_data)
        with self.assertRaises(ValueError) as context:
            validate_and_clean_csv(file_source)
        self.assertIn("balance went negative", str(context.exception))

        # Selling more than owned
        csv_data_2 = """ticker,date,transaction_type,quantity,price
MSFT,2025-06-15,Buy,50,410.00
MSFT,2025-06-16,Sell,60,420.00"""
        file_source_2 = io.StringIO(csv_data_2)
        with self.assertRaises(ValueError) as context:
            validate_and_clean_csv(file_source_2)
        self.assertIn("balance went negative", str(context.exception))

if __name__ == "__main__":
    unittest.main()
