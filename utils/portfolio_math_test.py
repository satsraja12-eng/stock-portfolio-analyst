import unittest
import pandas as pd
from datetime import datetime, timedelta
from utils.portfolio_math import calculate_fifo_holdings, calculate_portfolio_xirr

class TestPortfolioMath(unittest.TestCase):
    
    def setUp(self):
        # Setup a sample chronological transaction dataframe
        self.df = pd.DataFrame([
            {"ticker": "MSFT", "date": datetime(2025, 6, 15), "transaction_type": "Buy", "quantity": 50, "price": 410.00},
            {"ticker": "GOOGL", "date": datetime(2025, 8, 1), "transaction_type": "Buy", "quantity": 20, "price": 145.00},
            {"ticker": "NVDA", "date": datetime(2025, 9, 10), "transaction_type": "Buy", "quantity": 5, "price": 500.00},
            {"ticker": "MSFT", "date": datetime(2025, 11, 20), "transaction_type": "Buy", "quantity": 30, "price": 425.00},
            {"ticker": "NVDA", "date": datetime(2026, 1, 5), "transaction_type": "Sell", "quantity": 2, "price": 650.00},
            {"ticker": "CRM", "date": datetime(2026, 2, 18), "transaction_type": "Buy", "quantity": 15, "price": 280.00},
            {"ticker": "GOOGL", "date": datetime(2026, 4, 10), "transaction_type": "Sell", "quantity": 10, "price": 165.00},
            {"ticker": "ASTS", "date": datetime(2026, 5, 1), "transaction_type": "Buy", "quantity": 100, "price": 8.50}
        ])

    def test_fifo_holdings_calculation(self):
        holdings, realized_gains = calculate_fifo_holdings(self.df)
        
        # Verify active tickers are correct
        self.assertIn("MSFT", holdings)
        self.assertIn("GOOGL", holdings)
        self.assertIn("NVDA", holdings)
        self.assertIn("CRM", holdings)
        self.assertIn("ASTS", holdings)
        
        # Verify share counts
        self.assertEqual(holdings["MSFT"]["shares"], 80) # 50 + 30
        self.assertEqual(holdings["GOOGL"]["shares"], 10) # 20 - 10
        self.assertEqual(holdings["NVDA"]["shares"], 3) # 5 - 2
        self.assertEqual(holdings["CRM"]["shares"], 15)
        self.assertEqual(holdings["ASTS"]["shares"], 100)

        # Verify MSFT average cost: (50*410 + 30*425) / 80 = (20500 + 12750) / 80 = 33250 / 80 = 415.625
        self.assertAlmostEqual(holdings["MSFT"]["avg_cost"], 415.625)
        
        # Verify GOOGL realized gain: 10 shares sold at 165, bought at 145 (since it's FIFO, matched against first buy lot of 20 at 145)
        # Gain = 10 * (165 - 145) = 200.00
        self.assertEqual(realized_gains["GOOGL"], 200.00)
        
        # Verify NVDA realized gain: 2 shares sold at 650, bought at 500
        # Gain = 2 * (650 - 500) = 300.00
        self.assertEqual(realized_gains["NVDA"], 300.00)
        
        # Verify other active holdings lots are correct
        self.assertEqual(len(holdings["MSFT"]["lots"]), 2)
        self.assertEqual(len(holdings["GOOGL"]["lots"]), 1)
        self.assertEqual(holdings["GOOGL"]["lots"][0]["quantity"], 10) # 20 - 10 consumed

    def test_portfolio_xirr_calculation(self):
        holdings, _ = calculate_fifo_holdings(self.df)
        
        # Mock current prices
        current_prices = {
            "MSFT": 420.00,  # cost: 415.625 (Gain)
            "GOOGL": 170.00, # cost: 145.00  (Gain)
            "NVDA": 950.00,  # cost: 500.00  (Gain)
            "CRM": 290.00,   # cost: 280.00  (Gain)
            "ASTS": 9.00     # cost: 8.50    (Gain)
        }
        
        xirr = calculate_portfolio_xirr(self.df, current_prices, holdings)
        
        # Since all assets went up, XIRR must be positive and realistic
        self.assertTrue(xirr > 0)
        # Verify that XIRR is returned as a float rate (e.g. 15% to 30%)
        self.assertTrue(0.01 < xirr < 2.0)

if __name__ == "__main__":
    unittest.main()
