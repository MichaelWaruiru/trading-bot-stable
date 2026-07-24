import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SYMBOL = os.getenv("SYMBOL", "EURUSD")

DEFAULT_RISK_PERCENTAGE = float(os.getenv("RISK_PERCENTAGE", "1.0"))