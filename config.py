import os
from dotenv import load_dotenv
load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
TICKERS = {"10Y": "^TNX", "SP500": "^GSPC", "DXY": "DX-Y.NYB"}
# Thresholds in indicator's units: CPI percentage points, payrolls thousands.
THRESHOLDS = {"CPI YoY": 0.2, "Core CPI YoY": 0.2, "Nonfarm Payrolls": 50}
