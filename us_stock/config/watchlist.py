"""
관심 종목 및 섹터 매핑
"""
from typing import Dict, List

# =============================================================================
# 투자 유니버스
# =============================================================================

WATCHLIST: Dict[str, List[str]] = {
    # 대형 기술주 (Mega Cap Tech)
    "mega_tech": [
        "AAPL",   # Apple
        "MSFT",   # Microsoft
        "GOOGL",  # Alphabet
        "AMZN",   # Amazon
        "NVDA",   # NVIDIA
        "META",   # Meta
        "TSLA",   # Tesla
    ],

    # 반도체 (Semiconductor)
    "semiconductor": [
        "NVDA",   # NVIDIA
        "AMD",    # AMD
        "AVGO",   # Broadcom
        "QCOM",   # Qualcomm
        "INTC",   # Intel
        "MU",     # Micron
        "AMAT",   # Applied Materials
        "ASML",   # ASML
    ],

    # 소프트웨어/클라우드 (Software/Cloud)
    "software": [
        "CRM",    # Salesforce
        "ADBE",   # Adobe
        "NOW",    # ServiceNow
        "SNOW",   # Snowflake
        "PLTR",   # Palantir
        "NET",    # Cloudflare
        "DDOG",   # Datadog
        "CRWD",   # CrowdStrike
    ],

    # 핀테크 (Fintech)
    "fintech": [
        "V",      # Visa
        "MA",     # Mastercard
        "PYPL",   # PayPal
        "SQ",     # Block (Square)
        "COIN",   # Coinbase
    ],

    # 헬스케어 (Healthcare)
    "healthcare": [
        "UNH",    # UnitedHealth
        "JNJ",    # Johnson & Johnson
        "LLY",    # Eli Lilly
        "PFE",    # Pfizer
        "ABBV",   # AbbVie
        "MRK",    # Merck
        "TMO",    # Thermo Fisher
    ],

    # 소비재 (Consumer)
    "consumer": [
        "COST",   # Costco
        "WMT",    # Walmart
        "HD",     # Home Depot
        "NKE",    # Nike
        "SBUX",   # Starbucks
        "MCD",    # McDonald's
    ],

    # 금융 (Financials)
    "financials": [
        "JPM",    # JPMorgan
        "BAC",    # Bank of America
        "GS",     # Goldman Sachs
        "MS",     # Morgan Stanley
        "BLK",    # BlackRock
    ],

    # 에너지 (Energy)
    "energy": [
        "XOM",    # ExxonMobil
        "CVX",    # Chevron
        "COP",    # ConocoPhillips
        "SLB",    # Schlumberger
        "EOG",    # EOG Resources
    ],

    # AI/로보틱스 (AI/Robotics)
    "ai_robotics": [
        "NVDA",   # NVIDIA (중복)
        "GOOGL",  # Alphabet (중복)
        "MSFT",   # Microsoft (중복)
        "IBM",    # IBM
        "ORCL",   # Oracle
        "AI",     # C3.ai
        "PATH",   # UiPath
        "UPST",   # Upstart
    ],

    # 통신 (Communication)
    "communication": [
        "VZ",     # Verizon
        "T",      # AT&T
        "TMUS",   # T-Mobile
        "NFLX",   # Netflix
        "DIS",    # Disney
        "CMCSA",  # Comcast
    ],

    # 산업재 (Industrials)
    "industrials": [
        "CAT",    # Caterpillar
        "DE",     # Deere
        "BA",     # Boeing
        "HON",    # Honeywell
        "UPS",    # UPS
        "RTX",    # Raytheon
        "LMT",    # Lockheed Martin
        "GE",     # GE Aerospace
    ],

    # 리츠 (REITs)
    "reits": [
        "AMT",    # American Tower
        "PLD",    # Prologis
        "EQIX",   # Equinix
        "O",      # Realty Income
        "DLR",    # Digital Realty
    ],

    # ETF (벤치마크/모니터링용)
    "etf": [
        "SPY",    # S&P 500
        "QQQ",    # NASDAQ 100
        "IWM",    # Russell 2000
        "DIA",    # Dow Jones
        "TLT",    # 20+ Year Treasury
        "GLD",    # Gold
        "VIX",    # Volatility Index (모니터링용)
    ],
}

# =============================================================================
# 섹터 매핑
# =============================================================================

SECTOR_MAP: Dict[str, str] = {
    # Mega Tech
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Consumer Discretionary", "NVDA": "Technology", "META": "Technology",
    "TSLA": "Consumer Discretionary",

    # Semiconductor
    "AMD": "Technology", "AVGO": "Technology", "QCOM": "Technology",
    "INTC": "Technology", "MU": "Technology", "AMAT": "Technology",
    "ASML": "Technology",

    # Software
    "CRM": "Technology", "ADBE": "Technology", "NOW": "Technology",
    "SNOW": "Technology", "PLTR": "Technology", "NET": "Technology",
    "DDOG": "Technology", "CRWD": "Technology",

    # Fintech
    "V": "Financials", "MA": "Financials", "PYPL": "Financials",
    "SQ": "Financials", "COIN": "Financials",

    # Healthcare
    "UNH": "Healthcare", "JNJ": "Healthcare", "LLY": "Healthcare",
    "PFE": "Healthcare", "ABBV": "Healthcare", "MRK": "Healthcare",
    "TMO": "Healthcare",

    # Consumer
    "COST": "Consumer Staples", "WMT": "Consumer Staples",
    "HD": "Consumer Discretionary", "NKE": "Consumer Discretionary",
    "SBUX": "Consumer Discretionary", "MCD": "Consumer Discretionary",

    # Financials
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
    "MS": "Financials", "BLK": "Financials",

    # Energy
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
    "SLB": "Energy", "EOG": "Energy",

    # AI/Robotics
    "IBM": "Technology", "ORCL": "Technology", "AI": "Technology",
    "PATH": "Technology", "UPST": "Technology",

    # Communication
    "VZ": "Communication Services", "T": "Communication Services",
    "TMUS": "Communication Services", "NFLX": "Communication Services",
    "DIS": "Communication Services", "CMCSA": "Communication Services",

    # Industrials
    "CAT": "Industrials", "DE": "Industrials", "BA": "Industrials",
    "HON": "Industrials", "UPS": "Industrials", "RTX": "Industrials",
    "LMT": "Industrials", "GE": "Industrials",

    # REITs
    "AMT": "Real Estate", "PLD": "Real Estate", "EQIX": "Real Estate",
    "O": "Real Estate", "DLR": "Real Estate",
}

# =============================================================================
# 섹터 ETF 매핑
# =============================================================================

SECTOR_ETF: Dict[str, str] = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

# =============================================================================
# 목표 배분
# =============================================================================

TARGET_ALLOCATION: Dict[str, float] = {
    "Technology": 0.30,           # 기술 30%
    "Healthcare": 0.15,           # 헬스케어 15%
    "Financials": 0.15,           # 금융 15%
    "Consumer Discretionary": 0.10,  # 경기소비재 10%
    "Consumer Staples": 0.10,     # 필수소비재 10%
    "Energy": 0.05,               # 에너지 5%
    "Other": 0.05,                # 기타 5%
    "Cash": 0.10,                 # 현금 10%
}


def get_all_symbols() -> List[str]:
    """모든 관심 종목 반환 (중복 제거)"""
    all_symbols = set()
    for category, symbols in WATCHLIST.items():
        if category != "etf":  # ETF는 제외
            all_symbols.update(symbols)
    return sorted(list(all_symbols))


def get_sector(symbol: str) -> str:
    """종목의 섹터 반환"""
    return SECTOR_MAP.get(symbol, "Other")
