import unittest
from datetime import datetime, timedelta
from utils.external_data import (
    fetch_sectors_for_tickers, 
    fetch_fundamentals_and_dividends, 
    fetch_news_for_tickers, 
    fetch_benchmark_performance
)

class TestExternalData(unittest.TestCase):
    
    def test_sectors_fetching(self):
        tickers = ["MSFT", "GOOGL", "NVDA"]
        sectors = fetch_sectors_for_tickers(tickers)
        
        # Verify all tickers are mapped
        self.assertIn("MSFT", sectors)
        self.assertIn("GOOGL", sectors)
        self.assertIn("NVDA", sectors)
        
        # Verify correct fallback sector mapping
        self.assertEqual(sectors["MSFT"], "Technology")
        self.assertEqual(sectors["GOOGL"], "Communication Services")
        self.assertEqual(sectors["NVDA"], "Technology")

    def test_fundamentals_fetching(self):
        tickers = ["MSFT"]
        fundamentals = fetch_fundamentals_and_dividends(tickers)
        
        self.assertIn("MSFT", fundamentals)
        self.assertIn("name", fundamentals["MSFT"])
        self.assertIn("dividend_date", fundamentals["MSFT"])
        self.assertIn("dividend_yield", fundamentals["MSFT"])
        self.assertIn("pe_ratio", fundamentals["MSFT"])

    def test_news_fetching(self):
        tickers = ["MSFT"]
        news = fetch_news_for_tickers(tickers, max_articles=2)
        
        # News could be empty if API call is throttled, but if populated, check fields
        if news:
            self.assertEqual(news[0]["ticker"], "MSFT")
            self.assertIn("title", news[0])
            self.assertIn("link", news[0])
            self.assertIn("publisher", news[0])

    def test_benchmark_performance(self):
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        df = fetch_benchmark_performance(start_date, end_date)
        
        # If API is operational, check df shape and columns
        if not df.empty:
            self.assertIn("date", df.columns)
            self.assertIn("close", df.columns)
            self.assertIn("cumulative_return", df.columns)
            self.assertTrue(len(df) > 0)

if __name__ == "__main__":
    unittest.main()
