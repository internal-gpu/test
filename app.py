"""Stock Strategy Assistant — Streamlit Dashboard."""

import json
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from market_data import MarketData
from strategy import (
    list_strategies, load_strategy, save_strategy, delete_strategy,
    create_default_strategy, evaluate_signals,
)

st.set_page_config(page_title="Stock Strategy Assistant", page_icon="", layout="wide")

# ---------------------------------------------------------------------------
# Cached singletons
# ---------------------------------------------------------------------------

@st.cache_resource
def get_market():
    return MarketData()


def get_news_fetcher():
    from news_fetcher import NewsFetcher
    return NewsFetcher()


def get_analyzer():
    from analyzer import StockAnalyzer
    return StockAnalyzer()


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def build_price_chart(price_df, indicator_df, symbol):
    """Build a Plotly figure with candlestick + MAs + volume + RSI + MACD."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=[f"{symbol} Price", "Volume", "RSI (14)", "MACD"],
    )

    # --- Row 1: Candlestick + MAs + Bollinger ---
    fig.add_trace(go.Candlestick(
        x=price_df.index, open=price_df["Open"], high=price_df["High"],
        low=price_df["Low"], close=price_df["Close"], name="Price",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ), row=1, col=1)

    colors = {"MA5": "#ff9800", "MA10": "#2196f3", "MA20": "#9c27b0", "MA60": "#607d8b"}
    for ma, color in colors.items():
        if ma in price_df.columns:
            series = price_df[ma].dropna()
            if not series.empty:
                fig.add_trace(go.Scatter(
                    x=series.index, y=series, name=ma,
                    line=dict(width=1, color=color),
                ), row=1, col=1)

    if "BB_Upper" in price_df.columns:
        bb_u = price_df["BB_Upper"].dropna()
        bb_l = price_df["BB_Lower"].dropna()
        if not bb_u.empty:
            fig.add_trace(go.Scatter(
                x=bb_u.index, y=bb_u, name="BB Upper",
                line=dict(width=1, dash="dot", color="rgba(150,150,150,0.5)"),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=bb_l.index, y=bb_l, name="BB Lower",
                line=dict(width=1, dash="dot", color="rgba(150,150,150,0.5)"),
                fill="tonexty", fillcolor="rgba(150,150,150,0.07)",
            ), row=1, col=1)

    # --- Row 2: Volume ---
    vol_colors = ["#26a69a" if c >= o else "#ef5350"
                  for c, o in zip(price_df["Close"], price_df["Open"])]
    fig.add_trace(go.Bar(
        x=price_df.index, y=price_df["Volume"], name="Volume",
        marker_color=vol_colors, showlegend=False,
    ), row=2, col=1)

    # --- Row 3: RSI ---
    if "RSI" in indicator_df.columns:
        rsi = indicator_df["RSI"].dropna()
        fig.add_trace(go.Scatter(
            x=rsi.index, y=rsi, name="RSI",
            line=dict(color="#7e57c2", width=1.5),
        ), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)

    # --- Row 4: MACD ---
    if "MACD" in indicator_df.columns:
        macd = indicator_df["MACD"].dropna()
        sig = indicator_df["MACD_Signal"].dropna()
        hist = indicator_df["MACD_Hist"].dropna()

        fig.add_trace(go.Scatter(
            x=macd.index, y=macd, name="MACD",
            line=dict(color="#2196f3", width=1.5),
        ), row=4, col=1)
        fig.add_trace(go.Scatter(
            x=sig.index, y=sig, name="Signal",
            line=dict(color="#ff9800", width=1.5),
        ), row=4, col=1)
        hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in hist]
        fig.add_trace(go.Bar(
            x=hist.index, y=hist, name="Histogram",
            marker_color=hist_colors, showlegend=False,
        ), row=4, col=1)

    fig.update_layout(
        height=800, xaxis_rangeslider_visible=False,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=20),
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Vol", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)
    fig.update_yaxes(title_text="MACD", row=4, col=1)

    return fig


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Stock Strategy Assistant")

page = st.sidebar.radio("Navigate", [
    "Dashboard",
    "Stock Analysis",
    "Strategy Manager",
    "AI Analysis",
    "Chat",
])

# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------

if page == "Dashboard":
    st.header("Dashboard")

    strategies = list_strategies()
    if not strategies:
        st.info("No strategies found. Go to **Strategy Manager** to create one.")
        st.stop()

    selected_strategy = st.selectbox("Select Strategy", strategies)
    strat = load_strategy(selected_strategy)
    symbols = strat.get("symbols", [])

    if not symbols:
        st.warning("This strategy has no symbols configured.")
        st.stop()

    # Overview table
    market = get_market()
    st.subheader("Portfolio Overview")

    rows = []
    for sym in symbols:
        try:
            info = market.get_stock_info(sym)
            tech = market.calculate_technicals(sym)
            price = info.get("current_price", 0)
            prev = info.get("previous_close", price)
            change = ((price - prev) / prev * 100) if prev else 0
            rows.append({
                "Symbol": sym,
                "Name": info.get("name", ""),
                "Price": price,
                "Change %": round(change, 2),
                "RSI": tech.get("rsi_14"),
                "MA20": tech.get("ma20"),
                "Volume Ratio": tech.get("volume_ratio"),
                "P/E": info.get("pe_ratio"),
            })
        except Exception as e:
            rows.append({"Symbol": sym, "Name": f"Error: {e}"})

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.applymap(
                lambda v: "color: #26a69a" if isinstance(v, (int, float)) and v > 0
                else ("color: #ef5350" if isinstance(v, (int, float)) and v < 0 else ""),
                subset=["Change %"] if "Change %" in df.columns else [],
            ),
            use_container_width=True,
        )

    # Signal summary
    st.subheader("Strategy Signals")
    for sym in symbols:
        try:
            info = market.get_stock_info(sym)
            tech = market.calculate_technicals(sym)
            result = evaluate_signals(strat, tech, info)

            buy = result["buy_signals"]
            sell = result["sell_signals"]
            hold = result["hold_signals"]
            total = buy + sell + hold

            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            col1.markdown(f"**{sym}** ({info.get('name', '')})")
            col2.metric("Buy", buy)
            col3.metric("Sell", sell)
            col4.metric("Hold", hold)

            with st.expander(f"Signal details — {sym}"):
                for sig in result["signals"]:
                    icon = {"buy": ":green[BUY]", "sell": ":red[SELL]", "hold": "HOLD"}[sig["action"]]
                    st.markdown(f"- {icon} **{sig['name']}**: {sig['reason']}")
        except Exception as e:
            st.error(f"{sym}: {e}")

# ---------------------------------------------------------------------------
# Page: Stock Analysis
# ---------------------------------------------------------------------------

elif page == "Stock Analysis":
    st.header("Stock Analysis")

    col_input, col_period = st.columns([3, 1])
    symbol = col_input.text_input("Stock Symbol", value="AAPL", placeholder="e.g. AAPL, 0700.HK, 600519.SS").strip().upper()
    period = col_period.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

    if not symbol:
        st.stop()

    market = get_market()

    try:
        with st.spinner(f"Loading {symbol}..."):
            info = market.get_stock_info(symbol)
            tech = market.calculate_technicals(symbol)
            series = market.get_technicals_series(symbol, period=period)

        # Key metrics
        price = info.get("current_price", 0)
        prev = info.get("previous_close", price)
        change = ((price - prev) / prev * 100) if prev else 0

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Price", f"{price:.2f} {info.get('currency', '')}", f"{change:+.2f}%")
        m2.metric("RSI (14)", f"{tech.get('rsi_14', 'N/A')}")
        m3.metric("P/E", f"{info.get('pe_ratio', 'N/A')}")
        m4.metric("Market Cap", f"{info.get('market_cap', 0)/1e9:.1f}B" if info.get("market_cap") else "N/A")
        m5.metric("Volume Ratio", f"{tech.get('volume_ratio', 'N/A')}x")

        # Chart
        price_df = series["price_df"]
        indicator_df = series["indicator_df"]
        if not price_df.empty:
            fig = build_price_chart(price_df, indicator_df, symbol)
            st.plotly_chart(fig, use_container_width=True)

        # Technical summary
        with st.expander("Technical Indicators Detail"):
            tech_col1, tech_col2 = st.columns(2)
            with tech_col1:
                st.markdown("**Moving Averages**")
                for ma in ["ma5", "ma10", "ma20", "ma60"]:
                    val = tech.get(ma)
                    if val:
                        above = price > val
                        status = ":green[Above]" if above else ":red[Below]"
                        st.markdown(f"- {ma.upper()}: {val:.2f} ({status})")

            with tech_col2:
                st.markdown("**Oscillators**")
                st.markdown(f"- RSI (14): {tech.get('rsi_14', 'N/A')}")
                st.markdown(f"- MACD: {tech.get('macd', 'N/A')}")
                st.markdown(f"- MACD Signal: {tech.get('macd_signal', 'N/A')}")
                st.markdown(f"- MACD Histogram: {tech.get('macd_histogram', 'N/A')}")
                st.markdown(f"- Bollinger Upper: {tech.get('bollinger_upper', 'N/A')}")
                st.markdown(f"- Bollinger Lower: {tech.get('bollinger_lower', 'N/A')}")

        # Stock info
        with st.expander("Stock Info"):
            info_display = {k: v for k, v in info.items() if v is not None}
            st.json(info_display)

    except Exception as e:
        st.error(f"Failed to load data for {symbol}: {e}")


# ---------------------------------------------------------------------------
# Page: Strategy Manager
# ---------------------------------------------------------------------------

elif page == "Strategy Manager":
    st.header("Strategy Manager")

    tab_list, tab_create, tab_edit = st.tabs(["Strategies", "Create New", "Edit"])

    with tab_list:
        strategies = list_strategies()
        if not strategies:
            st.info("No strategies yet. Use the **Create New** tab to get started.")
        else:
            for name in strategies:
                try:
                    s = load_strategy(name)
                    with st.expander(f"{s.get('name', name)} — {s.get('style', '')} — {', '.join(s.get('symbols', []))}"):
                        st.markdown(f"**Description**: {s.get('description', '')}")
                        st.markdown(f"**Created**: {s.get('created_at', 'N/A')}")

                        st.markdown("**Rules**:")
                        for r in s.get("rules", []):
                            st.markdown(f"- `{r.get('type')}` — {r.get('name', '')}")

                        rm = s.get("risk_management", {})
                        st.markdown("**Risk Management**:")
                        st.markdown(f"- Max Position: {rm.get('max_position_pct', 'N/A')}%")
                        st.markdown(f"- Stop Loss: {rm.get('stop_loss_pct', 'N/A')}%")
                        st.markdown(f"- Take Profit: {rm.get('take_profit_pct', 'N/A')}%")

                        if s.get("notes"):
                            st.markdown(f"**Notes**: {s['notes']}")

                        if st.button(f"Delete '{name}'", key=f"del_{name}"):
                            delete_strategy(name)
                            st.rerun()
                except Exception as e:
                    st.error(f"{name}: {e}")

    with tab_create:
        st.subheader("Create New Strategy")
        with st.form("create_strategy"):
            name = st.text_input("Strategy Name", placeholder="e.g. my_tech_stocks")
            symbols_input = st.text_input("Symbols (comma-separated)", placeholder="AAPL, MSFT, NVDA")
            style = st.selectbox("Style", ["balanced", "conservative", "aggressive"])
            submitted = st.form_submit_button("Create")

            if submitted and name and symbols_input:
                symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
                create_default_strategy(name, symbols, style=style)
                st.success(f"Strategy '{name}' created! Go to **Edit** tab to customize rules.")
                st.rerun()

    with tab_edit:
        strategies = list_strategies()
        if not strategies:
            st.info("No strategies to edit.")
        else:
            edit_name = st.selectbox("Select Strategy to Edit", strategies, key="edit_select")
            strat = load_strategy(edit_name)

            st.subheader("Basic Info")
            strat["name"] = st.text_input("Display Name", value=strat.get("name", edit_name), key="edit_name")
            strat["description"] = st.text_input("Description", value=strat.get("description", ""), key="edit_desc")

            new_symbols = st.text_input(
                "Symbols (comma-separated)",
                value=", ".join(strat.get("symbols", [])),
                key="edit_symbols",
            )
            strat["symbols"] = [s.strip().upper() for s in new_symbols.split(",") if s.strip()]

            strat["style"] = st.selectbox(
                "Style", ["balanced", "conservative", "aggressive"],
                index=["balanced", "conservative", "aggressive"].index(strat.get("style", "balanced")),
                key="edit_style",
            )

            # Risk management
            st.subheader("Risk Management")
            rm = strat.get("risk_management", {})
            rc1, rc2, rc3, rc4 = st.columns(4)
            rm["max_position_pct"] = rc1.number_input("Max Position %", value=rm.get("max_position_pct", 20), min_value=1, max_value=100, key="rm_pos")
            rm["stop_loss_pct"] = rc2.number_input("Stop Loss %", value=rm.get("stop_loss_pct", 8), min_value=1, max_value=50, key="rm_sl")
            rm["take_profit_pct"] = rc3.number_input("Take Profit %", value=rm.get("take_profit_pct", 20), min_value=1, max_value=200, key="rm_tp")
            rm["max_total_exposure_pct"] = rc4.number_input("Max Exposure %", value=rm.get("max_total_exposure_pct", 80), min_value=1, max_value=100, key="rm_exp")
            strat["risk_management"] = rm

            # Rules editor
            st.subheader("Rules")
            rules = strat.get("rules", [])

            rule_types = {
                "rsi": {"params": ["oversold|30", "overbought|70"]},
                "ma_cross": {"params": ["fast|ma5", "slow|ma20"]},
                "price_vs_ma": {"params": ["ma|ma20", "threshold|5"]},
                "macd": {"params": []},
                "bollinger": {"params": []},
                "volume": {"params": ["high_ratio|2.0", "low_ratio|0.5"]},
                "pe_ratio": {"params": ["low|10", "high|30"]},
            }

            updated_rules = []
            for i, rule in enumerate(rules):
                with st.expander(f"Rule {i+1}: {rule.get('name', rule.get('type', '?'))}"):
                    rc1, rc2 = st.columns(2)
                    rule_type = rc1.selectbox(
                        "Type", list(rule_types.keys()),
                        index=list(rule_types.keys()).index(rule["type"]) if rule.get("type") in rule_types else 0,
                        key=f"rt_{i}",
                    )
                    rule_name = rc2.text_input("Name", value=rule.get("name", ""), key=f"rn_{i}")

                    rule_new = {"type": rule_type, "name": rule_name, "weight": 1}

                    # Show params for the selected type
                    params_def = rule_types.get(rule_type, {}).get("params", [])
                    if params_def:
                        pcols = st.columns(len(params_def))
                        for j, pdef in enumerate(params_def):
                            pname, pdefault = pdef.split("|")
                            current = rule.get(pname, pdefault)
                            try:
                                current = float(current)
                                rule_new[pname] = pcols[j].number_input(pname, value=current, key=f"rp_{i}_{j}")
                            except (ValueError, TypeError):
                                rule_new[pname] = pcols[j].text_input(pname, value=str(current), key=f"rp_{i}_{j}")

                    keep = st.checkbox("Keep this rule", value=True, key=f"rk_{i}")
                    if keep:
                        updated_rules.append(rule_new)

            # Add new rule
            with st.expander("Add New Rule"):
                new_type = st.selectbox("Type", list(rule_types.keys()), key="new_rt")
                new_name = st.text_input("Name", value="", key="new_rn")
                if st.button("Add Rule"):
                    new_rule = {"type": new_type, "name": new_name or new_type, "weight": 1}
                    for pdef in rule_types.get(new_type, {}).get("params", []):
                        pname, pdefault = pdef.split("|")
                        try:
                            new_rule[pname] = float(pdefault)
                        except ValueError:
                            new_rule[pname] = pdefault
                    updated_rules.append(new_rule)

            strat["rules"] = updated_rules

            # Notes
            strat["notes"] = st.text_area("Notes", value=strat.get("notes", ""), key="edit_notes")

            if st.button("Save Strategy", type="primary"):
                save_strategy(edit_name, strat)
                st.success(f"Strategy '{edit_name}' saved!")


# ---------------------------------------------------------------------------
# Page: AI Analysis
# ---------------------------------------------------------------------------

elif page == "AI Analysis":
    st.header("AI Analysis")

    col1, col2 = st.columns([3, 1])
    symbol = col1.text_input("Symbol", value="AAPL", key="ai_symbol").strip().upper()

    strategies = list_strategies()
    strategy_name = col2.selectbox("Strategy (optional)", ["None"] + strategies, key="ai_strat")

    if st.button("Run Full Analysis", type="primary"):
        if not symbol:
            st.warning("Enter a symbol.")
            st.stop()

        market = get_market()
        news = get_news_fetcher()
        analyzer = get_analyzer()

        progress = st.progress(0, text="Fetching stock data...")

        try:
            info = market.get_stock_info(symbol)
            tech = market.calculate_technicals(symbol)
            progress.progress(25, text="Evaluating strategy...")

            if strategy_name != "None":
                strat = load_strategy(strategy_name)
                signals = evaluate_signals(strat, tech, info)
            else:
                strat = {"risk_management": {"max_position_pct": 20, "stop_loss_pct": 8, "take_profit_pct": 20}}
                signals = {"signals": [], "note": "No strategy selected"}

            progress.progress(40, text="Searching latest news...")
            stock_news = news.search_stock_news(symbol, info.get("name"))

            progress.progress(70, text="Generating AI analysis...")
            analysis = analyzer.analyze(info, tech, signals, stock_news, strat)

            progress.progress(100, text="Done!")

            st.markdown("---")
            st.markdown(analysis)

            # Store in session for chat follow-up
            st.session_state["last_analysis"] = analysis
            st.session_state["last_analysis_symbol"] = symbol

        except Exception as e:
            st.error(f"Analysis failed: {e}")

    # Show previous analysis if exists
    if "last_analysis" in st.session_state and not st.session_state.get("_analysis_just_ran"):
        with st.expander(f"Previous analysis: {st.session_state.get('last_analysis_symbol', '')}"):
            st.markdown(st.session_state["last_analysis"])


# ---------------------------------------------------------------------------
# Page: Chat
# ---------------------------------------------------------------------------

elif page == "Chat":
    st.header("Chat with AI Assistant")

    # Init chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Context info
    context_parts = []
    if "last_analysis" in st.session_state:
        st.info(f"Context loaded: latest analysis of {st.session_state.get('last_analysis_symbol', 'unknown')}")
        context_parts.append(st.session_state["last_analysis"][:2000])

    # Display history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask about stocks, strategies, market..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        analyzer = get_analyzer()
        context = "\n".join(context_parts) if context_parts else None

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    reply = analyzer.chat(st.session_state.chat_messages, context=context)
                    st.markdown(reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"Error: {e}")

    # Clear chat
    if st.sidebar.button("Clear Chat History"):
        st.session_state.chat_messages = []
        st.rerun()
