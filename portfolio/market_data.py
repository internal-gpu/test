"""Yahoo Finance 行情数据封装"""

import yfinance as yf
import pandas as pd
from functools import lru_cache


_quote_cache: dict[str, dict] = {}


def get_quotes(tickers: list[str]) -> dict[str, dict]:
    """批量获取实时行情数据

    Returns: {ticker: {price, prev_close, day_change_pct, currency, name}}
    """
    if not tickers:
        return {}

    # 检查缓存
    uncached = [t for t in tickers if t not in _quote_cache]

    if uncached:
        batch = yf.Tickers(" ".join(uncached))
        for ticker in uncached:
            try:
                info = batch.tickers[ticker.replace(".", "-")].fast_info
                hist = batch.tickers[ticker.replace(".", "-")].history(period="2d")
                prev_close = hist['Close'].iloc[-2] if len(hist) >= 2 else info.get('previousClose', 0)
                price = info['lastPrice']
                _quote_cache[ticker] = {
                    'price': price,
                    'prev_close': prev_close,
                    'day_change_pct': ((price - prev_close) / prev_close * 100) if prev_close else 0,
                    'currency': info.get('currency', 'USD'),
                }
            except Exception:
                # fallback: 用 history 获取最新价
                try:
                    t = yf.Ticker(ticker)
                    hist = t.history(period="5d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                        prev_close = hist['Close'].iloc[-2] if len(hist) >= 2 else price
                        _quote_cache[ticker] = {
                            'price': price,
                            'prev_close': prev_close,
                            'day_change_pct': ((price - prev_close) / prev_close * 100) if prev_close else 0,
                            'currency': 'HKD' if '.HK' in ticker else 'USD',
                        }
                    else:
                        _quote_cache[ticker] = {
                            'price': 0, 'prev_close': 0,
                            'day_change_pct': 0, 'currency': 'USD',
                        }
                except Exception:
                    _quote_cache[ticker] = {
                        'price': 0, 'prev_close': 0,
                        'day_change_pct': 0, 'currency': 'USD',
                    }

    return {t: _quote_cache[t] for t in tickers if t in _quote_cache}


def get_history(tickers: list[str], period: str = "3mo") -> pd.DataFrame:
    """获取价格历史（用于相关性分析）

    Returns: DataFrame with tickers as columns, daily close prices
    """
    data = yf.download(tickers, period=period, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        return data['Close']
    return data


@lru_cache(maxsize=1)
def get_forex_rate(pair: str = "HKDUSD=X") -> float:
    """获取汇率"""
    try:
        t = yf.Ticker(pair)
        hist = t.history(period="5d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass
    return 0.128  # fallback HKD/USD


def clear_cache():
    """清除行情缓存"""
    _quote_cache.clear()
    get_forex_rate.cache_clear()
