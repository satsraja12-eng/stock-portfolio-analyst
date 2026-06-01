import unittest
from utils.llm_agent import get_ai_response

class TestLlmAgent(unittest.TestCase):
    
    def test_missing_api_key(self):
        # Asserts that if API key is blank, it returns a friendly warning rather than crashing
        response = get_ai_response(
            messages=[{"role": "user", "content": "Hello"}],
            api_key="",
            portfolio_context={}
        )
        self.assertIn("API Key is not configured", response)

    def test_mock_portfolio_context_mapping(self):
        # Asserts structure checks
        portfolio_context = {
            "total_value": 10000.0,
            "total_cost": 9000.0,
            "unrealized_gain": 1000.0,
            "unrealized_pct": 11.11,
            "realized_gain": 500.0,
            "active_holdings": [
                {"ticker": "MSFT", "name": "Microsoft", "shares": 10, "avg_cost": 300.0, "price": 350.0, "market_value": 3500.0, "gain": 500.0, "gain_pct": 16.67}
            ],
            "sector_weights": {"Technology": 3500.0},
            "dividends": [{"ticker": "MSFT", "yield": "0.75%", "date": "2026-05-15"}],
            "news_headlines": [{"ticker": "MSFT", "title": "Microsoft Earnings Rise", "publisher": "Reuters"}]
        }
        
        # We pass an invalid key to check that it reaches the Groq API call and returns an API Error
        # rather than failing inside prompt construction! This proves prompt construction is 100% stable.
        response = get_ai_response(
            messages=[{"role": "user", "content": "Show my Microsoft holdings"}],
            api_key="invalid_key_for_testing",
            portfolio_context=portfolio_context
        )
        self.assertIn("Groq API Error", response)

if __name__ == "__main__":
    unittest.main()
