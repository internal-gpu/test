"""Market data fetcher using yfinance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


class MarketData:
    """Fetch and process stock market data."""

    def get_stock_info(self, symbol):
        """Get basic stock information.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', '0700.HK', '600519.SS').

        Returns:
            Dict with stock info including name, price, market cap, etc.
        """
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "currency": info.get("currency", "N/A"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "previous_close": info.get("previousClose"),
            "open": info.get("open") or info.get("regularMarketOpen"),
            "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
            "volume": info.get("volume") or info.get("regularMarketVolume"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "50d_avg": info.get("fiftyDayAverage"),
            "200d_avg": info.get("twoHundredDayAverage"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
        }

    def get_price_history(self, symbol, period="3mo", interval="1d"):
        """Get historical price data.

        Args:
            symbol: Stock ticker symbol.
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max).
            interval: Data interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo).

        Returns:
            pandas DataFrame with OHLCV data.
        """
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period, interval=interval)

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
        bb_mid = ma20
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        # Volume analysis
        vol_avg_20 = df["Volume"].rolling(20).mean()

        latest = close.iloc[-1]
        result = {
            "current_price": round(latest, 2),
            "ma5": round(ma5.iloc[-1], 2) if len(ma5.dropna()) > 0 else None,
            "ma10": round(ma10.iloc[-1], 2) if len(ma10.dropna()) > 0 else None,
            "ma20": round(ma20.iloc[-1], 2) if len(ma20.dropna()) > 0 else None,
            "ma60": round(ma60.iloc[-1], 2) if len(ma60.dropna()) > 0 else None,
            "rsi_14": round(rsi.iloc[-1], 2) if len(rsi.dropna()) > 0 else None,
            "macd": round(macd_line.iloc[-1], 4) if len(macd_line.dropna()) > 0 else None,
            "macd_signal": round(signal_line.iloc[-1], 4) if len(signal_line.dropna()) > 0 else None,
            "macd_histogram": round(macd_hist.iloc[-1], 4) if len(macd_hist.dropna()) > 0 else None,
            "bollinger_upper": round(bb_upper.iloc[-1], 2) if len(bb_upper.dropna()) > 0 else None,
            "bollinger_lower": round(bb_lower.iloc[-1], 2) if len(bb_lower.dropna()) > 0 else None,
            "volume_ratio": round(df["Volume"].iloc[-1] / vol_avg_20.iloc[-1], 2) if vol_avg_20.iloc[-1] > 0 else None,
            "price_change_5d": round((latest / close.iloc[-6] - 1) * 100, 2) if len(close) >= 6 else None,
            "price_change_20d": round((latest / close.iloc[-21] - 1) * 100, 2) if len(close) >= 21 else None,
            # Trend signals
            "above_ma20": latest > ma20.iloc[-1] if len(ma20.dropna()) > 0 else None,
            "above_ma60": latest > ma60.iloc[-1] if len(ma60.dropna()) > 0 else None,
            "ma5_cross_ma20": (ma5.iloc[-1] > ma20.iloc[-1]) != (ma5.iloc[-2] > ma20.iloc[-2]) if len(ma5.dropna()) > 1 and len(ma20.dropna()) > 1 else None,
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

        # Price DataFrame with overlays
        price_df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        price_df["MA5"] = close.rolling(5).mean()
        price_df["MA10"] = close.rolling(10).mean()
        price_df["MA20"] = close.rolling(20).mean()
        price_df["MA60"] = close.rolling(60).mean()

        bb_std = close.rolling(20).std()
        price_df["BB_Upper"] = price_df["MA20"] + 2 * bb_std
        price_df["BB_Lower"] = price_df["MA20"] - 2 * bb_std

        # Indicator DataFrame
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
