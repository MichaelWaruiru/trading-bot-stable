import unittest
from app import calculate_risk, calculate_profit_loss

class TestTradingBot(unittest.TestCase):
    def test_calculate_risk(self):
        self.assertEqual(calculate_risk(1000, 1), 10)

    def test_calculate_profit_loss(self):
        self.assertEqual(calculate_profit_loss(1, 1.5, "long"), 0.5)
        self.assertEqual(calculate_profit_loss(1, 0.5, "short"), 0.5)

if __name__ == "__main__":
    unittest.main()