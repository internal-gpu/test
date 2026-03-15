"""Strategy engine — load, evaluate, and manage trading strategies."""

import os
import yaml
from datetime import datetime
from pathlib import Path

STRATEGIES_DIR = Path("strategies")


def ensure_strategies_dir():
    """Create strategies directory if it doesn't exist."""
    STRATEGIES_DIR.mkdir(exist_ok=True)


def load_strategy(name):
    """Load a strategy from YAML file.

    Args:
        name: Strategy name (filename without .yaml extension).

    Returns:
        Dict with strategy configuration.
    """
    path = STRATEGIES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Strategy '{name}' not found at {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def save_strategy(name, strategy):
    """Save a strategy to YAML file.

    Args:
        name: Strategy name.
        strategy: Dict with strategy configuration.
    """
    ensure_strategies_dir()
    path = STRATEGIES_DIR / f"{name}.yaml"
    strategy["updated_at"] = datetime.now().isoformat()
    path.write_text(yaml.dump(strategy, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")


def list_strategies():
    """List all available strategies.

    Returns:
        List of strategy names.
    """
    ensure_strategies_dir()
    return [p.stem for p in STRATEGIES_DIR.glob("*.yaml")]


def delete_strategy(name):
    """Delete a strategy file.

    Args:
        name: Strategy name.
    """
    path = STRATEGIES_DIR / f"{name}.yaml"
    if path.exists():
        path.unlink()


def evaluate_signals(strategy, technicals, stock_info):
    """Evaluate a strategy's rules against current market data.

    This produces rule-level signal results that feed into the AI analyzer
    for final recommendation.

    Args:
        strategy: Strategy dict loaded from YAML.
        technicals: Dict of technical indicator values from MarketData.
        stock_info: Dict of basic stock info from MarketData.

    Returns:
        Dict with signal evaluation results.
    """
    results = {
        "strategy_name": strategy.get("name", "unnamed"),
        "symbol": stock_info.get("symbol"),
        "evaluated_at": datetime.now().isoformat(),
        "signals": [],
        "buy_signals": 0,
        "sell_signals": 0,
        "hold_signals": 0,
    }

    rules = strategy.get("rules", [])
    for rule in rules:
        signal = _evaluate_rule(rule, technicals, stock_info)
        results["signals"].append(signal)
        if signal["action"] == "buy":
            results["buy_signals"] += 1
        elif signal["action"] == "sell":
            results["sell_signals"] += 1
        else:
            results["hold_signals"] += 1

    total = len(rules)
    if total > 0:
        results["buy_ratio"] = results["buy_signals"] / total
        results["sell_ratio"] = results["sell_signals"] / total
    else:
        results["buy_ratio"] = 0
        results["sell_ratio"] = 0

    return results


def _evaluate_rule(rule, technicals, stock_info):
    """Evaluate a single rule.

    Args:
        rule: Rule dict from strategy YAML.
        technicals: Technical indicators dict.
        stock_info: Stock info dict.

    Returns:
        Dict with signal result for this rule.
    """
    rule_type = rule.get("type", "")
    name = rule.get("name", rule_type)

    try:
        if rule_type == "rsi":
            return _eval_rsi(rule, technicals, name)
        elif rule_type == "ma_cross":
            return _eval_ma_cross(rule, technicals, name)
        elif rule_type == "price_vs_ma":
            return _eval_price_vs_ma(rule, technicals, name)
        elif rule_type == "macd":
            return _eval_macd(rule, technicals, name)
        elif rule_type == "bollinger":
            return _eval_bollinger(rule, technicals, name)
        elif rule_type == "volume":
            return _eval_volume(rule, technicals, name)
        elif rule_type == "pe_ratio":
            return _eval_pe(rule, stock_info, name)
        else:
            return {"name": name, "action": "hold", "reason": f"Unknown rule type: {rule_type}"}
    except (KeyError, TypeError) as e:
        return {"name": name, "action": "hold", "reason": f"Data unavailable: {e}"}


def _eval_rsi(rule, technicals, name):
    rsi = technicals.get("rsi_14")
    if rsi is None:
        return {"name": name, "action": "hold", "reason": "RSI data unavailable"}

    oversold = rule.get("oversold", 30)
    overbought = rule.get("overbought", 70)

    if rsi < oversold:
        return {"name": name, "action": "buy", "reason": f"RSI={rsi} < {oversold} (oversold)", "value": rsi}
    elif rsi > overbought:
        return {"name": name, "action": "sell", "reason": f"RSI={rsi} > {overbought} (overbought)", "value": rsi}
    return {"name": name, "action": "hold", "reason": f"RSI={rsi} in neutral zone [{oversold}-{overbought}]", "value": rsi}


def _eval_ma_cross(rule, technicals, name):
    fast = rule.get("fast", "ma5")
    slow = rule.get("slow", "ma20")
    fast_val = technicals.get(fast)
    slow_val = technicals.get(slow)

    if fast_val is None or slow_val is None:
        return {"name": name, "action": "hold", "reason": f"MA data unavailable"}

    if fast_val > slow_val:
        return {"name": name, "action": "buy", "reason": f"{fast}({fast_val}) > {slow}({slow_val}) golden cross zone"}
    else:
        return {"name": name, "action": "sell", "reason": f"{fast}({fast_val}) < {slow}({slow_val}) death cross zone"}


def _eval_price_vs_ma(rule, technicals, name):
    ma_key = rule.get("ma", "ma20")
    ma_val = technicals.get(ma_key)
    price = technicals.get("current_price")

    if ma_val is None or price is None:
        return {"name": name, "action": "hold", "reason": "Data unavailable"}

    pct = (price - ma_val) / ma_val * 100
    threshold = rule.get("threshold", 5)

    if pct < -threshold:
        return {"name": name, "action": "buy", "reason": f"Price {pct:.1f}% below {ma_key} (threshold: -{threshold}%)"}
    elif pct > threshold:
        return {"name": name, "action": "sell", "reason": f"Price {pct:.1f}% above {ma_key} (threshold: +{threshold}%)"}
    return {"name": name, "action": "hold", "reason": f"Price {pct:.1f}% from {ma_key} (within ±{threshold}%)"}


def _eval_macd(rule, technicals, name):
    macd = technicals.get("macd")
    signal = technicals.get("macd_signal")
    hist = technicals.get("macd_histogram")

    if macd is None or signal is None:
        return {"name": name, "action": "hold", "reason": "MACD data unavailable"}

    if hist is not None and hist > 0 and macd > signal:
        return {"name": name, "action": "buy", "reason": f"MACD({macd:.4f}) > Signal({signal:.4f}), histogram positive"}
    elif hist is not None and hist < 0 and macd < signal:
        return {"name": name, "action": "sell", "reason": f"MACD({macd:.4f}) < Signal({signal:.4f}), histogram negative"}
    return {"name": name, "action": "hold", "reason": f"MACD neutral (hist={hist})"}


def _eval_bollinger(rule, technicals, name):
    price = technicals.get("current_price")
    upper = technicals.get("bollinger_upper")
    lower = technicals.get("bollinger_lower")

    if price is None or upper is None or lower is None:
        return {"name": name, "action": "hold", "reason": "Bollinger data unavailable"}

    if price <= lower:
        return {"name": name, "action": "buy", "reason": f"Price({price}) at/below lower band({lower})"}
    elif price >= upper:
        return {"name": name, "action": "sell", "reason": f"Price({price}) at/above upper band({upper})"}
    return {"name": name, "action": "hold", "reason": f"Price({price}) within bands [{lower}-{upper}]"}


def _eval_volume(rule, technicals, name):
    vol_ratio = technicals.get("volume_ratio")
    if vol_ratio is None:
        return {"name": name, "action": "hold", "reason": "Volume data unavailable"}

    high_threshold = rule.get("high_ratio", 2.0)
    low_threshold = rule.get("low_ratio", 0.5)

    if vol_ratio > high_threshold:
        return {"name": name, "action": "buy", "reason": f"Volume ratio {vol_ratio}x > {high_threshold}x (high activity)"}
    elif vol_ratio < low_threshold:
        return {"name": name, "action": "sell", "reason": f"Volume ratio {vol_ratio}x < {low_threshold}x (low activity)"}
    return {"name": name, "action": "hold", "reason": f"Volume ratio {vol_ratio}x normal", "value": vol_ratio}


def _eval_pe(rule, stock_info, name):
    pe = stock_info.get("pe_ratio")
    if pe is None:
        return {"name": name, "action": "hold", "reason": "P/E data unavailable"}

    low = rule.get("low", 10)
    high = rule.get("high", 30)

    if pe < low:
        return {"name": name, "action": "buy", "reason": f"P/E={pe:.1f} < {low} (potentially undervalued)"}
    elif pe > high:
        return {"name": name, "action": "sell", "reason": f"P/E={pe:.1f} > {high} (potentially overvalued)"}
    return {"name": name, "action": "hold", "reason": f"P/E={pe:.1f} in normal range [{low}-{high}]"}


def create_default_strategy(name, symbols, style="balanced"):
    """Create a default strategy template.

    Args:
        name: Strategy name.
        symbols: List of stock symbols to track.
        style: One of 'conservative', 'balanced', 'aggressive'.

    Returns:
        The created strategy dict.
    """
    base = {
        "name": name,
        "description": f"{style.capitalize()} trading strategy",
        "symbols": symbols,
        "style": style,
        "created_at": datetime.now().isoformat(),
        "rules": [],
        "risk_management": {
            "max_position_pct": 20,
            "stop_loss_pct": 8,
            "take_profit_pct": 20,
            "max_total_exposure_pct": 80,
        },
        "notes": "",
    }

    if style == "conservative":
        base["rules"] = [
            {"type": "rsi", "name": "RSI Conservative", "oversold": 25, "overbought": 75, "weight": 1},
            {"type": "price_vs_ma", "name": "Price vs MA60", "ma": "ma60", "threshold": 8, "weight": 1},
            {"type": "macd", "name": "MACD Trend", "weight": 1},
            {"type": "pe_ratio", "name": "Valuation", "low": 8, "high": 25, "weight": 1},
        ]
        base["risk_management"]["max_position_pct"] = 15
        base["risk_management"]["stop_loss_pct"] = 5
    elif style == "aggressive":
        base["rules"] = [
            {"type": "rsi", "name": "RSI Aggressive", "oversold": 35, "overbought": 65, "weight": 1},
            {"type": "ma_cross", "name": "MA5/MA10 Cross", "fast": "ma5", "slow": "ma10", "weight": 1},
            {"type": "macd", "name": "MACD Momentum", "weight": 1},
            {"type": "bollinger", "name": "Bollinger Breakout", "weight": 1},
            {"type": "volume", "name": "Volume Surge", "high_ratio": 1.5, "low_ratio": 0.6, "weight": 1},
        ]
        base["risk_management"]["max_position_pct"] = 30
        base["risk_management"]["stop_loss_pct"] = 12
        base["risk_management"]["take_profit_pct"] = 30
    else:  # balanced
        base["rules"] = [
            {"type": "rsi", "name": "RSI Standard", "oversold": 30, "overbought": 70, "weight": 1},
            {"type": "ma_cross", "name": "MA5/MA20 Cross", "fast": "ma5", "slow": "ma20", "weight": 1},
            {"type": "macd", "name": "MACD Signal", "weight": 1},
            {"type": "bollinger", "name": "Bollinger Position", "weight": 1},
            {"type": "pe_ratio", "name": "Valuation Check", "low": 10, "high": 30, "weight": 1},
        ]

    save_strategy(name, base)
    return base
