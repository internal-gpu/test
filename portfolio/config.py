"""YAML 配置加载"""

import os
import yaml
from .models import Portfolio, Holding, CashPosition

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'portfolio.yaml')

DEFAULT_SETTINGS = {
    'default_currency': 'USD',
    'hkd_usd_rate': 0.128,
    'risk_tolerance': 'aggressive',
    'rebalance_threshold_pct': 5,
}


def load_portfolio(path: str = None) -> Portfolio:
    """从 YAML 文件加载持仓配置"""
    if path is None:
        path = DEFAULT_CONFIG_PATH

    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"配置文件不存在: {path}\n请复制 portfolio.example.yaml 为 portfolio.yaml")

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    holdings = []
    for h in data.get('holdings', []):
        holdings.append(Holding(
            ticker=h['ticker'],
            shares=float(h['shares']),
            avg_cost=float(h['avg_cost']),
        ))

    cash = []
    for c in data.get('cash', []):
        cash.append(CashPosition(
            currency=c['currency'],
            amount=float(c['amount']),
        ))

    watchlist = data.get('watchlist', [])
    settings = {**DEFAULT_SETTINGS, **data.get('settings', {})}

    return Portfolio(holdings=holdings, cash=cash, watchlist=watchlist, settings=settings)


def save_portfolio(portfolio: Portfolio, path: str = None):
    """保存持仓配置到 YAML"""
    if path is None:
        path = os.path.abspath(DEFAULT_CONFIG_PATH)

    data = {
        'holdings': [
            {'ticker': h.ticker, 'shares': h.shares, 'avg_cost': h.avg_cost}
            for h in portfolio.holdings
        ],
        'cash': [
            {'currency': c.currency, 'amount': c.amount}
            for c in portfolio.cash
        ],
        'watchlist': portfolio.watchlist,
        'settings': portfolio.settings,
    }

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
