"""TEFAS (Türkiye Elektronik Fon Alım Satım Platformu) veri servisi.

Kullanılan endpoint'ler:
  - Arama  : POST /Service.asmx/GetAllFunds  (ASP.NET ScriptService)
  - Fiyat  : POST /api/DB/BindHistoryInfo    (form-encoded)
"""
import logging
from datetime import date, timedelta
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

TEFAS_BASE = "https://www.tefas.gov.tr"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_BIND_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Origin": TEFAS_BASE,
    "Referer": f"{TEFAS_BASE}/TarihselVeriler.aspx",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": _UA,
}
_SEARCH_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": TEFAS_BASE,
    "Referer": f"{TEFAS_BASE}/TarihselVeriler.aspx",
    "User-Agent": _UA,
}

# Geçerli fon tipleri
FUND_TYPES = {
    "YAT": "Yatırım Fonu",
    "EMK": "Emeklilik Fonu",
    "BYF": "Borsa Yatırım Fonu",
}


async def search_funds(query: str, fund_type: str = "YAT") -> list[dict]:
    """Fon adı veya kodu ile arama yapar.

    Returns:
        list of {"code": str, "name": str, "fund_type": str}
    """
    query = query.strip()
    if len(query) < 2:
        return []
    if fund_type not in FUND_TYPES:
        fund_type = "YAT"

    url = f"{TEFAS_BASE}/Service.asmx/GetAllFunds"
    body = {"prefixText": query.upper(), "count": 30, "contextKey": fund_type}
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            resp = await client.post(url, json=body, headers=_SEARCH_HEADERS)
            if resp.status_code != 200:
                logger.warning("TEFAS search HTTP %s", resp.status_code)
                return []
            data = resp.json()
        results = []
        for item in data.get("d", []):
            # Format 1 (JSON string): '{"First":"IKP - FON ADI","Second":"IKP"}'
            # Format 2 (pipe): "AAK AKASYA PORTFÖY|AAK"
            # Format 3 (plain): "AAK AKASYA PORTFÖY"
            import json as _json
            code = name = ""
            if isinstance(item, str) and item.startswith("{"):
                try:
                    obj = _json.loads(item)
                    code = obj.get("Second", "").strip()
                    name = obj.get("First", "").strip()
                except Exception:
                    pass
            elif isinstance(item, dict):
                code = item.get("Second", item.get("code", "")).strip()
                name = item.get("First", item.get("name", "")).strip()
            elif "|" in item:
                name, code = item.rsplit("|", 1)
                code = code.strip(); name = name.strip()
            else:
                parts = item.split(" ", 1)
                code = parts[0].strip()
                name = item.strip()
            if code:
                results.append({"code": code, "name": name, "fund_type": fund_type})
        return results
    except Exception as exc:
        logger.warning("TEFAS search error: %s", exc)
        return []


async def get_fund_price(code: str, fund_type: str = "YAT") -> Optional[dict]:
    """Fon için güncel NAV fiyatı döner.

    Returns:
        {"price": float, "currency": "TRY", "change_percent": float,
         "trend": str, "name": str, "code": str, "fund_type": str}
        or None on failure.
    """
    if fund_type not in FUND_TYPES:
        fund_type = "YAT"

    today = date.today()
    start = today - timedelta(days=7)  # hafta sonu / tatil toleransı
    url = f"{TEFAS_BASE}/api/DB/BindHistoryInfo"
    payload = {
        "fontip": fund_type,
        "fonkod": code.upper().strip(),
        "bastarih": start.strftime("%d.%m.%Y"),
        "bittarih": today.strftime("%d.%m.%Y"),
    }
    try:
        async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
            resp = await client.post(url, data=payload, headers=_BIND_HEADERS)
            if resp.status_code != 200:
                logger.warning("TEFAS price HTTP %s for %s", resp.status_code, code)
                return None
            data = resp.json()
        rows = data.get("data", [])
        if not rows:
            return None

        # API yeniden eskiye sıralar, ilk satır en güncel fiyat
        latest = rows[0]

        def _f(val: object) -> Optional[float]:
            if val is None:
                return None
            try:
                return float(str(val).replace(",", "."))
            except (ValueError, TypeError):
                return None

        price = _f(latest.get("FIYAT") or latest.get("fiyat"))
        if price is None:
            return None

        # GUNLUKGETIRI alanı yoksa önceki günden hesapla
        change = _f(latest.get("GUNLUKGETIRI") or latest.get("gunlukgetiri"))
        if change is None and len(rows) >= 2:
            prev_price = _f(rows[1].get("FIYAT") or rows[1].get("fiyat"))
            if prev_price and prev_price != 0:
                change = ((price - prev_price) / prev_price) * 100
        change = change or 0.0
        name = (latest.get("FONUNVAN") or latest.get("fonunvan") or code).strip()

        return {
            "price": price,
            "currency": "TRY",
            "change_percent": change,
            "trend": "up" if change > 0 else ("down" if change < 0 else "neutral"),
            "name": name,
            "code": code.upper(),
            "fund_type": fund_type,
        }
    except Exception as exc:
        logger.warning("TEFAS price error for %s: %s", code, exc)
        return None
