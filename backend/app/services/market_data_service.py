"""Market data service — Google Finance scraper using data-last-price attribute."""
import re
import aiohttp
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_GOOGLE_FINANCE_URL = "https://www.google.com/finance/quote/{symbol}"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

_EXCHANGE_PREFIXES = {"IST", "NYMEX", "NYSE", "NASDAQ", "LON", "PAR", "TYO", "FRA", "EPA", "ETR"}

_CURRENCY_CODES = {
    "TRY", "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "CNY", "RUB",
    "INR", "BRL", "MXN", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "RON",
}

# Pattern for embedded price arrays: [price, change_amount, change_pct, int, int, int]
_PRICE_ARRAY_RE = re.compile(
    r'\[([-+]?\d+\.?\d*(?:[Ee][-+]?\d+)?),([-+]?\d+\.?\d*(?:[Ee][-+]?\d+)?),([-+]?\d+\.?\d*(?:[Ee][-+]?\d+)?),\d+,\d+,\d+\]'
)


def _to_google_finance_symbol(symbol: str) -> str:
    """Convert user-entered symbol to Google Finance URL format (TICKER:EXCHANGE).

    Examples:
        IST:GARAN       -> GARAN:IST
        NYMEX:BZW00     -> BZW00:NYMEX
        USDTRY          -> USD-TRY
        CURRENCY:USDTRY -> USD-TRY
        USD-TRY         -> USD-TRY  (unchanged)
        GARAN:IST       -> GARAN:IST (unchanged)
    """
    s = symbol.upper().strip().replace(" ", "")

    for prefix in ("CURRENCY:", "FX:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break

    if ":" in s:
        left, right = s.split(":", 1)
        if left in _EXCHANGE_PREFIXES:
            s = f"{right}:{left}"

    # Currency pair without hyphen: USDTRY -> USD-TRY
    no_colon = s.replace("-", "")
    if ":" not in no_colon and len(no_colon) == 6:
        base, quote = no_colon[:3], no_colon[3:]
        if base in _CURRENCY_CODES or quote in _CURRENCY_CODES:
            return f"{base}-{quote}"

    return s


def _extract_change_percent(html: str, price: float) -> Optional[float]:
    """Extract change percent from embedded script arrays in Google Finance page.

    Google Finance embeds data arrays like:
        [126.5, 1, 0.7968128, 2, 2, 2]        (stocks: index 2 = change%)
        [44.4448, -0.0343, -0.07711486, 4, 4, 3]  (forex: index 2 = change%)

    Finds the array whose first element is closest to the known price (within 1%).
    """
    best_match = None
    best_diff = float("inf")

    for m in _PRICE_ARRAY_RE.finditer(html):
        try:
            arr_price = float(m.group(1))
            diff = abs(arr_price - price)
            rel_diff = diff / max(abs(price), 1e-9)
            if rel_diff < 0.02 and diff < best_diff:  # within 2%
                best_diff = diff
                best_match = float(m.group(3))
        except ValueError:
            continue

    return best_match


class MarketDataService:
    @staticmethod
    async def fetch_google_finance_price(symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current price from Google Finance using data-last-price attribute.

        Accepts various symbol formats (IST:GARAN, GARAN:IST, USDTRY, USD-TRY, etc.)
        and converts to the correct Google Finance URL format before fetching.
        """
        symbol = symbol.replace(" ", "").upper()
        gf_symbol = _to_google_finance_symbol(symbol)
        url = _GOOGLE_FINANCE_URL.format(symbol=gf_symbol)

        logger.info(f"Fetching market data: {symbol} -> GF:{gf_symbol}")

        try:
            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error(f"Google Finance HTTP {resp.status} for {gf_symbol}")
                        return None
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            price_tag = soup.find(attrs={"data-last-price": True})
            if not price_tag:
                logger.warning(f"No data-last-price found for {gf_symbol}")
                return None

            price_raw = price_tag.get("data-last-price")
            try:
                price = float(price_raw)
            except (TypeError, ValueError):
                logger.warning(f"Cannot parse price '{price_raw}' for {gf_symbol}")
                return None

            # Currency: stocks use data-currency-code, forex uses data-target
            currency = (
                price_tag.get("data-currency-code")
                or price_tag.get("data-target")
                or "USD"
            ).upper()

            # Change percent from embedded script arrays
            change_pct = _extract_change_percent(html, price)
            change_percent: Optional[Decimal] = None
            trend = "neutral"
            if change_pct is not None:
                change_percent = Decimal(str(round(change_pct, 4)))
                trend = "up" if change_pct > 0 else ("down" if change_pct < 0 else "neutral")

            return {
                "price": Decimal(str(price)),
                "currency": currency,
                "change_percent": change_percent,
                "trend": trend,
            }

        except Exception as e:
            logger.error(f"Error fetching {symbol} ({gf_symbol}): {e}")
            return None
