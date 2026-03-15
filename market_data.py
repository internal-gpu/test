"""Market data fetcher using Twelve Data API."""

import json
import os
import time
import hashlib
from pathlib import Path

import requests
import pandas as pd

CACHE_DIR = Path(".cache")
CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


class MarketData:
    """Fetch and process stock market data via Twelve Data."""

    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("TWELVEDATA_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Twelve Data API key required. "
                "Set TWELVEDATA_API_KEY in .env or pass api_key=."
            )
        CACHE_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _request(self, endpoint, params, cache_ttl=CACHE_TTL_SECONDS):
        """Make a cached request to Twelve Data.

        Args:
            endpoint: API endpoint path (e.g. '/quote', '/time_series').
            params: Dict of query parameters (without apikey).
            cache_ttl: Cache time-to-live in seconds.

        Returns:
            Parsed JSON (dict or list).
        """
        params["apikey"] = self.api_key
        cache_key = hashlib.md5(
            json.dumps({"ep": endpoint, **params}, sort_keys=True).encode()
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.json"

        # Check cache
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < cache_ttl:
                return json.loads(cache_file.read_text())

        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Error handling
        if isinstance(data, dict):
            if data.get("code") == 429:
                raise RuntimeError(f"Twelve Data rate limit: {data.get('message', '')}")
            if data.get("status") == "error":
                raise RuntimeError(f"Twelve Data error: {data.get('message', data)}")

        cache_file.write_text(json.dumps(data))
        return data

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_stock_info(self, symbol):
        """Get basic stock information.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT').

        Returns:
            Dict with stock info including name, price, market cap, etc.
        """
        # /quote — real-time price + basic stats
        quote = self._request("/quote", {"symbol": symbol})

        # /statistics — fundamentals (PE, market cap, etc.)
        # Twelve Data free tier may not include this, so we handle gracefully
        stats = {}
        try:
            stats = self._request("/statistics", {"symbol": symbol}, cache_ttl=3600)
            if isinstance(stats, dict) and "statistics" in stats:
                stats = stats["statistics"]
            else:
                stats = {}
        except Exception:
            stats = {}

        # /profile — company name, sector, industry
        profile = {}
        try:
            profile = self._request("/profile", {"symbol": symbol}, cache_ttl=86400)
        except Exception:
            profile = {}

        current_price = _float(quote.get("close"))
        previous_close = _float(quote.get("previous_close"))

        # Extract stats safely
        valuations = stats.get("valuations_metrics", {}) if isinstance(stats, dict) else {}
        financials = stats.get("financial_highlights", {}) if isinstance(stats, dict) else {}
        stock_stats = stats.get("stock_statistics", {}) if isinstance(stats, dict) else {}

        return {
            "symbol": symbol,
            "name": quote.get("name") or profile.get("name", symbol),
            "currency": quote.get("currency", "USD"),
            "current_price": current_price,
            "previous_close": previous_close,
            "open": _float(quote.get("open")),
            "day_high": _float(quote.get("high")),
            "day_low": _float(quote.get("low")),
            "volume": _int(quote.get("volume")),
            "market_cap": _float(valuations.get("market_capitalization")),
            "pe_ratio": _float(valuations.get("trailing_pe")),
            "forward_pe": _float(valuations.get("forward_pe")),
            "dividend_yield": _float(financials.get("dividend_yield")),
            "52w_high": _float(quote.get("fifty_two_week", {}).get("high")) if isinstance(quote.get("fifty_two_week"), dict) else _float(stock_stats.get("weeks_52_high")),
            "52w_low": _float(quote.get("fifty_two_week", {}).get("low")) if isinstance(quote.get("fifty_two_week"), dict) else _float(stock_stats.get("weeks_52_low")),
            "50d_avg": _float(stock_stats.get("50_day_ma")),
            "200d_avg": _float(stock_stats.get("200_day_ma")),
            "sector": profile.get("sector", "N/A"),
            "industry": profile.get("industry", "N/A"),
        }

    def get_price_history(self, symbol, period="3mo", interval="1d"):
        """Get historical price data.

        Args:
            symbol: Stock ticker symbol.
            period: Time period (1mo, 3mo, 6mo, 1y, 2y, 5y).
            interval: Data interval (default '1day' for Twelve Data).

        Returns:
            pandas DataFrame with OHLCV data, DatetimeIndex, sorted ascending.
        """
        # Map period to outputsize (number of data points)
        period_map = {
            "1mo": 22, "3mo": 66, "6mo": 130,
            "1y": 252, "2y": 504, "5y": 1260,
        }
        outputsize = period_map.get(period, 130)

        data = self._request("/time_series", {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": str(outputsize),
        })

        values = data.get("values", [])
        if not values:
            return pd.DataFrame()

        rows = []
        for v in values:
            rows.append({
                "Date": pd.Timestamp(v["datetime"]),
                "Open": float(v["open"]),
                "High": float(v["high"]),
                "Low": float(v["low"]),
                "Close": float(v["close"]),
                "Volume": int(v["volume"]),
            })

        df = pd.DataFrame(rows).set_index("Date").sort_index()
        return df

    def calculate_technicals(self, symbol, period="6mo"):
        """Calculate key technical indicators.

        Args:
            symbol: Stock ticker symbol.
            period: Time period for historical data.

        Returns:
            Dict with technical indicator values.
        """
        df = self.get_price_history(symbol, period=period)
        if df.empty:
            return {}

        close = df["Close"]

        # Moving averages
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        # RSI (14-day)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        # Bollinger Bands (20-day)
        bb_std = close.rolling(20).std()
        bb_upper = ma20 + 2 * bb_std
        bb_lower = ma20 - 2 * bb_std

        # Volume analysis
        vol_avg_20 = df["Volume"].rolling(20).mean()

        latest = close.iloc[-1]
        result = {
            "current_price": round(latest, 2),
            "ma5": _round(ma5.iloc[-1]) if len(ma5.dropna()) > 0 else None,
            "ma10": _round(ma10.iloc[-1]) if len(ma10.dropna()) > 0 else None,
            "ma20": _round(ma20.iloc[-1]) if len(ma20.dropna()) > 0 else None,
            "ma60": _round(ma60.iloc[-1]) if len(ma60.dropna()) > 0 else None,
            "rsi_14": _round(rsi.iloc[-1]) if len(rsi.dropna()) > 0 else None,
            "macd": _round(macd_line.iloc[-1], 4) if len(macd_line.dropna()) > 0 else None,
            "macd_signal": _round(signal_line.iloc[-1], 4) if len(signal_line.dropna()) > 0 else None,
            "macd_histogram": _round(macd_hist.iloc[-1], 4) if len(macd_hist.dropna()) > 0 else None,
            "bollinger_upper": _round(bb_upper.iloc[-1]) if len(bb_upper.dropna()) > 0 else None,
            "bollinger_lower": _round(bb_lower.iloc[-1]) if len(bb_lower.dropna()) > 0 else None,
            "volume_ratio": _round(df["Volume"].iloc[-1] / vol_avg_20.iloc[-1]) if vol_avg_20.iloc[-1] > 0 else None,
            "price_change_5d": _round((latest / close.iloc[-6] - 1) * 100) if len(close) >= 6 else None,
            "price_change_20d": _round((latest / close.iloc[-21] - 1) * 100) if len(close) >= 21 else None,
            "above_ma20": bool(latest > ma20.iloc[-1]) if len(ma20.dropna()) > 0 else None,
            "above_ma60": bool(latest > ma60.iloc[-1]) if len(ma60.dropna()) > 0 else None,
            "ma5_cross_ma20": bool((ma5.iloc[-1] > ma20.iloc[-1]) != (ma5.iloc[-2] > ma20.iloc[-2])) if len(ma5.dropna()) > 1 and len(ma20.dropna()) > 1 else None,
        }
        return result

    def get_technicals_series(self, symbol, period="6mo"):
        """Calculate technical indicators as full time-series DataFrames for charting.

        Args:
            symbol: Stock ticker symbol.
            period: Time period for historical data.

        Returns:
            Dict with 'price_df' (OHLCV + MAs + Bollinger) and 'indicator_df' (RSI, MACD).
        """
        df = self.get_price_history(symbol, period=period)
        if df.empty:
            return {"price_df": pd.DataFrame(), "indicator_df": pd.DataFrame()}

        close = df["Close"]

        price_df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        price_df["MA5"] = close.rolling(5).mean()
        price_df["MA10"] = close.rolling(10).mean()
        price_df["MA20"] = close.rolling(20).mean()
        price_df["MA60"] = close.rolling(60).mean()

        bb_std = close.rolling(20).std()
        price_df["BB_Upper"] = price_df["MA20"] + 2 * bb_std
        price_df["BB_Lower"] = price_df["MA20"] - 2 * bb_std

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        indicator_df = pd.DataFrame({
            "RSI": rsi,
            "MACD": macd_line,
            "MACD_Signal": signal_line,
            "MACD_Hist": macd_hist,
        }, index=df.index)

        return {"price_df": price_df, "indicator_df": indicator_df}

    def get_multi_stock_summary(self, symbols):
        """Get summary data for multiple stocks.

        Args:
            symbols: List of ticker symbols.

        Returns:
            List of dicts with summary info per stock.
        """
        results = []
        for sym in symbols:
            try:
                info = self.get_stock_info(sym)
                technicals = self.calculate_technicals(sym)
                results.append({**info, "technicals": technicals})
            except Exception as e:
                results.append({"symbol": sym, "error": str(e)})
        return results


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _float(val):
    """Safely convert to float."""
    if val is None or val == "" or val == "None" or val == "-":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _int(val):
    """Safely convert to int."""
    if val is None or val == "" or val == "None":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _round(val, decimals=2):
    """Safely round a value."""
    if val is None or pd.isna(val):
        return None
    return round(float(val), decimals)
