"""数据模型定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AIChainSegment(Enum):
    """AI 价值链六大板块"""
    MODELS_CLOUD = "Models/Cloud"
    CHIPS_GPU = "Chips/GPU"
    OPTICAL_NETWORKING = "Optical/Networking"
    STORAGE = "Storage"
    HPC_INFRA = "HPC/Infrastructure"
    MINING_TO_HPC = "Mining-to-HPC"


class Market(Enum):
    HK = "HK"
    US = "US"


@dataclass
class StockMeta:
    """AI 链路股票池元数据"""
    ticker: str
    name: str
    name_cn: str
    market: Market
    segment: AIChainSegment
    sub_theme: str
    ai_chain_score: float  # 0-100, AI 营收纯度
    notes: str = ""


@dataclass
class Holding:
    """持仓头寸"""
    ticker: str
    shares: float
    avg_cost: float
    segment: Optional[AIChainSegment] = None


@dataclass
class CashPosition:
    currency: str  # "HKD" or "USD"
    amount: float


@dataclass
class Portfolio:
    """完整持仓状态"""
    holdings: list = field(default_factory=list)
    cash: list = field(default_factory=list)
    watchlist: list = field(default_factory=list)
    settings: dict = field(default_factory=dict)


@dataclass
class EnrichedHolding:
    """持仓 + 实时行情数据"""
    holding: Holding
    meta: Optional[StockMeta]
    current_price: float
    market_value: float
    unrealized_pnl: float
    pnl_pct: float
    day_change_pct: float
    weight_pct: float  # 占总市值百分比
    market_value_usd: float = 0.0  # USD 标准化市值
