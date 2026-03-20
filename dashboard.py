import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pyupbit
import yfinance as yf
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
from deep_translator import GoogleTranslator

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

# 환경변수 로드
load_dotenv()

# ============================================================================
# 공통 함수
# ============================================================================

@st.cache_resource
def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def format_krw(value):
    if pd.isna(value) or value is None:
        return "0"
    try:
        return f"{float(value):,.0f}"
    except:
        return str(value)

def format_usd(value):
    if pd.isna(value) or value is None:
        return "$0"
    try:
        return f"${float(value):,.2f}"
    except:
        return str(value)

@st.cache_data(ttl=3600)
def translate_to_korean(text):
    if not text or pd.isna(text):
        return ""
    try:
        translator = GoogleTranslator(source='en', target='ko')
        return translator.translate(text[:4500] if len(text) > 4500 else text)
    except Exception as e:
        return f"번역 실패: {e}"

# ============================================================================
# 코인 관련 함수들
# ============================================================================

@st.cache_resource
def get_upbit_client():
    access = os.getenv("UPBIT_ACCESS_KEY")
    secret = os.getenv("UPBIT_SECRET_KEY")
    if not access or not secret:
        return None
    try:
        return pyupbit.Upbit(access, secret)
    except:
        return None

@st.cache_data(ttl=60)
def get_trades_from_supabase(days=30):
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        response = supabase.table("trades").select("*").gte("timestamp", cutoff).order("timestamp", desc=True).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            ts = pd.to_datetime(df['timestamp'])
            df['timestamp'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_upbit_orders(market="KRW-BTC"):
    upbit = get_upbit_client()
    if not upbit:
        return pd.DataFrame()
    try:
        orders = upbit.get_order(market, state="done")
        if not orders:
            return pd.DataFrame()
        df = pd.DataFrame(orders)
        df['created_at'] = pd.to_datetime(df['created_at'])
        ts = df['created_at']
        df['created_at'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz is not None else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
        numeric_cols = ['volume', 'price', 'executed_volume', 'paid_fee']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.sort_values('created_at', ascending=False)
    except:
        return pd.DataFrame()

def get_trading_fees(orders_df, days=30):
    if orders_df.empty:
        return 0
    try:
        cutoff = datetime.now(KST) - timedelta(days=days)
        recent = orders_df[orders_df['created_at'] >= cutoff]
        if 'paid_fee' in recent.columns:
            return recent['paid_fee'].sum()
        return 0
    except:
        return 0

@st.cache_data(ttl=300)
def get_deposits_from_upbit():
    upbit = get_upbit_client()
    if not upbit:
        return pd.DataFrame()
    try:
        records = []
        deposits = upbit.get_deposits(currency="KRW")
        if deposits:
            for d in deposits:
                if d.get('state') == 'accepted':
                    records.append({
                        'id': d.get('uuid', ''),
                        'created_at': pd.to_datetime(d.get('created_at')),
                        'type': 'deposit',
                        'amount': float(d.get('amount', 0)),
                        'memo': '업비트 원화 입금'
                    })
        withdraws = upbit.get_withdraws(currency="KRW")
        if withdraws:
            for w in withdraws:
                if w.get('state') == 'done':
                    records.append({
                        'id': w.get('uuid', ''),
                        'created_at': pd.to_datetime(w.get('created_at')),
                        'type': 'withdraw',
                        'amount': float(w.get('amount', 0)),
                        'memo': '업비트 원화 출금'
                    })
        if records:
            df = pd.DataFrame(records)
            ts = df['created_at']
            df['created_at'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz is not None else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df.sort_values('created_at', ascending=False)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_manual_deposits():
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("deposits").select("*").order("created_at", desc=True).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            ts = pd.to_datetime(df['created_at'])
            df['created_at'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_expenses():
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("expenses").select("*").order("created_at", desc=True).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            ts = pd.to_datetime(df['created_at'])
            df['created_at'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def get_all_deposits():
    upbit = get_deposits_from_upbit()
    manual = get_manual_deposits()
    if upbit.empty and manual.empty:
        return pd.DataFrame()
    elif upbit.empty:
        return manual
    elif manual.empty:
        return upbit
    return pd.concat([upbit, manual], ignore_index=True).sort_values('created_at', ascending=False)

@st.cache_data(ttl=30)
def get_current_btc_price():
    try:
        return pyupbit.get_current_price("KRW-BTC")
    except:
        return None

def add_deposit(amount, deposit_type, memo):
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("deposits").insert({"amount": float(amount), "type": deposit_type, "memo": memo}).execute()
        return True
    except:
        return False

def delete_deposit(deposit_id):
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("deposits").delete().eq("id", deposit_id).execute()
        return True
    except:
        return False

def add_expense(category, name, amount, period, memo):
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("expenses").insert({"category": category, "name": name, "amount": float(amount), "period": period, "memo": memo}).execute()
        return True
    except:
        return False

def delete_expense(expense_id):
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("expenses").delete().eq("id", expense_id).execute()
        return True
    except:
        return False

def calculate_monthly_expenses(expenses_df, trading_fees=0, days=30):
    total = 0
    by_cat = {'api': 0, 'server': 0, 'trading_fee': 0, 'other': 0}
    monthly_trading_fee = trading_fees * (30 / days) if days > 0 else trading_fees
    by_cat['trading_fee'] = monthly_trading_fee
    total += monthly_trading_fee
    if not expenses_df.empty:
        for _, row in expenses_df.iterrows():
            amount = float(row['amount'])
            period = row.get('period', 'monthly')
            cat = row.get('category', 'other')
            if period == 'monthly':
                monthly = amount
            elif period == 'daily':
                monthly = amount * 30
            elif period == 'yearly':
                monthly = amount / 12
            else:
                monthly = amount * (30 / days)
            total += monthly
            by_cat[cat] = by_cat.get(cat, 0) + monthly
    return total, by_cat

def calculate_performance(trades_df, deposits_df, expenses_df, current_btc_price, days=30, trading_fees=0):
    if trades_df.empty:
        return {}
    df_sorted = trades_df.sort_values('timestamp')
    last = df_sorted.iloc[-1]
    price = current_btc_price or last['btc_krw_price']
    current_total = last['krw_balance'] + last['btc_balance'] * price
    total_dep = deposits_df[deposits_df['type'] == 'deposit']['amount'].sum() if not deposits_df.empty else 0
    total_wd = deposits_df[deposits_df['type'] == 'withdraw']['amount'].sum() if not deposits_df.empty else 0
    net_dep = total_dep - total_wd
    monthly_exp, exp_by_cat = calculate_monthly_expenses(expenses_df, trading_fees, days)
    real_profit = current_total - net_dep
    real_rate = (real_profit / net_dep * 100) if net_dep > 0 else 0
    net_profit = real_profit - monthly_exp
    net_rate = (net_profit / net_dep * 100) if net_dep > 0 else 0
    return {
        'current_total': current_total,
        'total_deposits': total_dep,
        'total_withdrawals': total_wd,
        'net_deposits': net_dep,
        'real_profit': real_profit,
        'real_rate': real_rate,
        'monthly_expenses': monthly_exp,
        'expenses_by_cat': exp_by_cat,
        'net_profit': net_profit,
        'net_rate': net_rate,
        'total_trades': len(trades_df),
        'buy_count': len(trades_df[trades_df['decision'] == 'buy']),
        'sell_count': len(trades_df[trades_df['decision'] == 'sell']),
        'hold_count': len(trades_df[trades_df['decision'] == 'hold']),
        'scheduled_count': len(trades_df[trades_df['source'] == 'scheduled']) if 'source' in trades_df.columns else 0,
        'triggered_count': len(trades_df[trades_df['source'] == 'triggered']) if 'source' in trades_df.columns else 0,
        'stop_loss_count': len(trades_df[trades_df['source'] == 'stop_loss']) if 'source' in trades_df.columns else 0,
        'take_profit_count': len(trades_df[trades_df['source'] == 'take_profit']) if 'source' in trades_df.columns else 0
    }

# ============================================================================
# 미국 주식 관련 함수들
# ============================================================================

@st.cache_data(ttl=60)
def get_us_stock_trades(days=30):
    """미국 주식 거래 기록 조회"""
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        response = supabase.table("us_stock_trades").select("*").gte("created_at", cutoff).order("created_at", desc=True).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            ts = pd.to_datetime(df['created_at'])
            df['created_at'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_us_portfolio_snapshots(days=30):
    """포트폴리오 스냅샷 조회"""
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        response = supabase.table("us_stock_portfolio_snapshots").select("*").gte("created_at", cutoff).order("created_at", desc=True).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            ts = pd.to_datetime(df['created_at'])
            df['created_at'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_us_stock_deposits():
    """미국 주식 입출금 내역 조회"""
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("us_stock_deposits").select("*").order("created_at", desc=True).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            ts = pd.to_datetime(df['created_at'])
            df['created_at'] = ts.dt.tz_convert('Asia/Seoul') if ts.dt.tz else ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def add_us_stock_deposit(amount, deposit_type, memo):
    """미국 주식 입출금 추가"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    try:
        supabase.table("us_stock_deposits").insert({
            "amount": float(amount),
            "type": deposit_type,
            "memo": memo
        }).execute()
        return True
    except:
        return False

def calculate_us_stock_performance(portfolio_df, deposits_df, trades_df):
    """미국 주식 실질 수익 계산"""
    if portfolio_df.empty:
        return {}

    latest = portfolio_df.iloc[0]
    current_total = latest.get('total_value', 0)

    # 입출금 계산
    total_deposits = 0
    total_withdrawals = 0
    if not deposits_df.empty:
        total_deposits = deposits_df[deposits_df['type'] == 'deposit']['amount'].sum()
        total_withdrawals = deposits_df[deposits_df['type'] == 'withdraw']['amount'].sum()
    net_deposits = total_deposits - total_withdrawals

    # 실현 손익 (거래 기록에서)
    realized_pnl = 0
    if not trades_df.empty and 'pnl' in trades_df.columns:
        realized_pnl = trades_df['pnl'].sum()

    # 미실현 손익
    unrealized_pnl = latest.get('unrealized_pnl', 0)

    # 실질 수익 = 현재 총자산 - 순입금
    real_profit = current_total - net_deposits if net_deposits > 0 else unrealized_pnl
    real_rate = (real_profit / net_deposits * 100) if net_deposits > 0 else 0

    return {
        'current_total': current_total,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'net_deposits': net_deposits,
        'realized_pnl': realized_pnl,
        'unrealized_pnl': unrealized_pnl,
        'real_profit': real_profit,
        'real_rate': real_rate,
    }

@st.cache_data(ttl=300)
def get_market_indices():
    """주요 시장 지수 조회"""
    indices = {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^DJI": "Dow Jones",
        "^VIX": "VIX",
    }
    result = {}
    for symbol, name in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                result[name] = {
                    "price": current,
                    "change": current - prev,
                    "change_pct": (current - prev) / prev * 100,
                }
        except:
            pass
    return result

@st.cache_data(ttl=300)
def get_stock_price(symbol: str):
    """개별 종목 가격 조회"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if not hist.empty:
            return {
                "price": hist['Close'].iloc[-1],
                "change_pct": (hist['Close'].iloc[-1] / hist['Close'].iloc[-2] - 1) * 100 if len(hist) > 1 else 0
            }
    except:
        pass
    return None

@st.cache_data(ttl=300)
def get_sector_performance():
    """섹터 성과 조회"""
    sector_etfs = {
        "XLK": "Technology",
        "XLF": "Financials",
        "XLV": "Healthcare",
        "XLE": "Energy",
        "XLY": "Consumer Disc.",
        "XLP": "Consumer Staples",
        "XLI": "Industrials",
    }
    result = {}
    for symbol, sector in sector_etfs.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                result[sector] = {
                    "change_pct": (current - prev) / prev * 100,
                }
        except:
            pass
    return result

# ============================================================================
# 코인 차트 함수들
# ============================================================================

def create_asset_chart(df, deposits_df, current_price, start_date=None):
    if df.empty:
        return go.Figure()
    df_sorted = df.sort_values('timestamp').copy()
    if start_date is not None:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        start_datetime = start_datetime.replace(tzinfo=KST)
        df_sorted = df_sorted[df_sorted['timestamp'] >= start_datetime]
    if df_sorted.empty:
        fig = go.Figure()
        fig.add_annotation(text="데이터 없음", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=280, template='plotly_dark')
        return fig
    price = current_price or df_sorted['btc_krw_price'].iloc[-1]
    df_sorted['total'] = df_sorted['krw_balance'] + df_sorted['btc_balance'] * price
    initial = df_sorted['total'].iloc[0]
    df_sorted['change'] = df_sorted['total'] - initial
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['change'],
        mode='lines', name='자산 증감',
        line=dict(color='#00D4AA', width=2),
        fill='tozeroy', fillcolor='rgba(0, 212, 170, 0.1)'
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=280, template='plotly_dark',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    return fig

def create_profit_chart(df, deposits_df, current_price, start_date=None):
    if df.empty:
        return go.Figure()
    df_sorted = df.sort_values('timestamp').copy()
    if start_date is not None:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        start_datetime = start_datetime.replace(tzinfo=KST)
        df_sorted = df_sorted[df_sorted['timestamp'] >= start_datetime]
    if df_sorted.empty:
        fig = go.Figure()
        fig.add_annotation(text="데이터 없음", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=280, template='plotly_dark')
        return fig
    net_deposits = 0
    if not deposits_df.empty:
        total_dep = deposits_df[deposits_df['type'] == 'deposit']['amount'].sum()
        total_wd = deposits_df[deposits_df['type'] == 'withdraw']['amount'].sum()
        net_deposits = total_dep - total_wd
    df_sorted['total'] = df_sorted['krw_balance'] + df_sorted['btc_balance'] * current_price
    df_sorted['profit'] = df_sorted['total'] - net_deposits
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['profit'],
        mode='lines+markers', name='실질 수익',
        line=dict(color='#00D4AA', width=2),
        marker=dict(size=4),
        fill='tozeroy', fillcolor='rgba(0, 212, 170, 0.1)'
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=280, template='plotly_dark',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    return fig

def create_btc_chart(df):
    if df.empty:
        return go.Figure()
    df_sorted = df.sort_values('timestamp')
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['btc_balance'],
        mode='lines', name='BTC',
        line=dict(color='#F7931A', width=2),
        fill='tozeroy', fillcolor='rgba(247, 147, 26, 0.1)'
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=200, template='plotly_dark',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    return fig

def create_decision_chart(df):
    if df.empty:
        return go.Figure()
    counts = df['decision'].value_counts()
    colors = {'buy': '#00D4AA', 'sell': '#FF6B6B', 'hold': '#4ECDC4'}
    labels = {'buy': '매수', 'sell': '매도', 'hold': '홀드'}
    fig = go.Figure(data=[go.Pie(
        labels=[labels.get(d, d) for d in counts.index],
        values=counts.values,
        marker_colors=[colors.get(d, '#888') for d in counts.index],
        hole=0.6, textinfo='percent', textfont_size=12
    )])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=180, template='plotly_dark',
        showlegend=True, legend=dict(orientation='h', y=-0.1)
    )
    return fig

def create_expense_chart(by_cat):
    if not by_cat or sum(by_cat.values()) == 0:
        fig = go.Figure()
        fig.add_annotation(text="비용 없음", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=180, template='plotly_dark')
        return fig
    labels_map = {'api': 'API', 'server': '서버', 'trading_fee': '거래수수료', 'other': '기타'}
    colors_map = {'api': '#FF6B6B', 'server': '#4ECDC4', 'trading_fee': '#F7931A', 'other': '#95A5A6'}
    labels, values, colors = [], [], []
    for cat, val in by_cat.items():
        if val > 0:
            labels.append(labels_map.get(cat, cat))
            values.append(val)
            colors.append(colors_map.get(cat, '#888'))
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        marker_colors=colors, hole=0.6,
        textinfo='percent', textfont_size=12
    )])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=180, template='plotly_dark',
        showlegend=True, legend=dict(orientation='h', y=-0.1)
    )
    return fig

# ============================================================================
# 미국 주식 차트 함수들
# ============================================================================

def create_us_portfolio_chart(df):
    """미국 주식 포트폴리오 추이"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="데이터 없음", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=280, template='plotly_dark')
        return fig

    df_sorted = df.sort_values('created_at').copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['created_at'], y=df_sorted['total_value'],
        mode='lines', name='총 자산',
        line=dict(color='#00D4AA', width=2),
        fill='tozeroy', fillcolor='rgba(0, 212, 170, 0.1)'
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=280, template='plotly_dark',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    return fig

def create_us_pnl_chart(df):
    """미국 주식 손익 추이"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="데이터 없음", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=280, template='plotly_dark')
        return fig

    df_sorted = df.sort_values('created_at').copy()
    if 'unrealized_pnl' not in df_sorted.columns:
        df_sorted['unrealized_pnl'] = 0

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['created_at'], y=df_sorted['unrealized_pnl'],
        mode='lines+markers', name='미실현 손익',
        line=dict(color='#4ECDC4', width=2),
        marker=dict(size=4)
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=280, template='plotly_dark',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    return fig

def create_sector_chart(sectors):
    """섹터 성과 차트"""
    if not sectors:
        fig = go.Figure()
        fig.add_annotation(text="데이터 없음", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=200, template='plotly_dark')
        return fig

    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1]['change_pct'], reverse=True)
    names = [s[0] for s in sorted_sectors]
    changes = [s[1]['change_pct'] for s in sorted_sectors]
    colors = ['#00D4AA' if c >= 0 else '#FF6B6B' for c in changes]

    fig = go.Figure(data=[go.Bar(
        x=changes, y=names,
        orientation='h',
        marker_color=colors
    )])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=200, template='plotly_dark',
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False),
    )
    return fig

def create_us_trade_decision_chart(df):
    """미국 주식 거래 결정 파이 차트"""
    if df.empty or 'action' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="거래 없음", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=180, template='plotly_dark')
        return fig

    counts = df['action'].value_counts()
    colors = {'buy': '#00D4AA', 'sell': '#FF6B6B', 'stop_loss': '#F7931A', 'take_profit': '#4ECDC4'}
    labels = {'buy': '매수', 'sell': '매도', 'stop_loss': '손절', 'take_profit': '익절'}

    fig = go.Figure(data=[go.Pie(
        labels=[labels.get(d, d) for d in counts.index],
        values=counts.values,
        marker_colors=[colors.get(d, '#888') for d in counts.index],
        hole=0.6, textinfo='percent', textfont_size=12
    )])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=180, template='plotly_dark',
        showlegend=True, legend=dict(orientation='h', y=-0.1)
    )
    return fig

# ============================================================================
# 코인 대시보드
# ============================================================================

def render_coin_dashboard(days, chart_start_date):
    """코인 대시보드 렌더링"""
    trades_df = get_trades_from_supabase(days)
    deposits_df = get_all_deposits()
    expenses_df = get_expenses()
    orders_df = get_upbit_orders()
    trading_fees = get_trading_fees(orders_df, days)
    btc_price = get_current_btc_price()

    # 헤더
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 💰 비트코인 자동매매")
    with col2:
        if btc_price:
            st.metric("BTC", f"₩{format_krw(btc_price)}")

    if trades_df.empty:
        st.warning("거래 기록이 없습니다.")
        return

    perf = calculate_performance(trades_df, deposits_df, expenses_df, btc_price, days, trading_fees)
    latest = trades_df.iloc[0]
    btc_val = latest['btc_balance'] * (btc_price or latest['btc_krw_price'])
    total_asset = latest['krw_balance'] + btc_val

    # 현재 자산
    st.markdown("#### 현재 자산")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BTC 보유", f"{latest['btc_balance']:.6f}")
    c2.metric("BTC 가치", f"₩{format_krw(btc_val)}")
    c3.metric("KRW 보유", f"₩{format_krw(latest['krw_balance'])}")
    c4.metric("총 자산", f"₩{format_krw(total_asset)}")

    # 투자 성과
    st.markdown("#### 투자 성과")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("순입금", f"₩{format_krw(perf.get('net_deposits', 0))}")
    c2.metric("현재 총자산", f"₩{format_krw(perf.get('current_total', 0))}")
    c3.metric("실질수익", f"₩{format_krw(perf.get('real_profit', 0))}", f"{perf.get('real_rate', 0):+.2f}%")
    c4.metric("운영비용", f"₩{format_krw(perf.get('monthly_expenses', 0))}/월")
    c5.metric("순수익", f"₩{format_krw(perf.get('net_profit', 0))}", f"{perf.get('net_rate', 0):+.2f}%")

    # 차트
    st.markdown("#### 차트")
    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"자산 증감 ({chart_start_date} 이후)")
        st.plotly_chart(create_asset_chart(trades_df, deposits_df, btc_price, chart_start_date), use_container_width=True, config={'displayModeBar': False})
    with c2:
        st.caption(f"실질 수익 추이 ({chart_start_date} 이후)")
        st.plotly_chart(create_profit_chart(trades_df, deposits_df, btc_price, chart_start_date), use_container_width=True, config={'displayModeBar': False})

    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("BTC 보유량")
        st.plotly_chart(create_btc_chart(trades_df), use_container_width=True, config={'displayModeBar': False})
    with c2:
        st.caption("거래 결정")
        st.plotly_chart(create_decision_chart(trades_df), use_container_width=True, config={'displayModeBar': False})
    with c3:
        st.caption("비용 분포")
        st.plotly_chart(create_expense_chart(perf.get('expenses_by_cat', {})), use_container_width=True, config={'displayModeBar': False})

    # 기록 탭
    st.markdown("#### 기록")
    tab1, tab2, tab3, tab4 = st.tabs(["거래", "체결내역", "입출금", "비용"])

    with tab1:
        if not trades_df.empty:
            cols = ['timestamp', 'decision', 'percentage']
            if 'source' in trades_df.columns:
                cols.append('source')
            if 'model' in trades_df.columns:
                cols.append('model')
            if 'pnl_percentage' in trades_df.columns:
                cols.append('pnl_percentage')
            cols.extend(['btc_balance', 'btc_krw_price', 'reason'])

            page_size = 15
            total_records = len(trades_df)
            total_pages = max(1, (total_records + page_size - 1) // page_size)

            if 'coin_trades_page' not in st.session_state:
                st.session_state.coin_trades_page = 1

            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
            with col1:
                if st.button('⏮️', key='coin_first'):
                    st.session_state.coin_trades_page = 1
            with col2:
                if st.button('◀️', key='coin_prev'):
                    if st.session_state.coin_trades_page > 1:
                        st.session_state.coin_trades_page -= 1
            with col3:
                st.markdown(f"<p style='text-align:center; margin-top:8px;'>{st.session_state.coin_trades_page} / {total_pages}</p>", unsafe_allow_html=True)
            with col4:
                if st.button('▶️', key='coin_next'):
                    if st.session_state.coin_trades_page < total_pages:
                        st.session_state.coin_trades_page += 1
            with col5:
                if st.button('⏭️', key='coin_last'):
                    st.session_state.coin_trades_page = total_pages

            start_idx = (st.session_state.coin_trades_page - 1) * page_size
            end_idx = start_idx + page_size
            page_data = trades_df.iloc[start_idx:end_idx].copy()

            display = page_data[[c for c in cols if c in page_data.columns]].copy()
            display['timestamp'] = display['timestamp'].dt.strftime('%m/%d %H:%M')
            display['decision'] = display['decision'].map({'buy': '🟢매수', 'sell': '🔴매도', 'hold': '⚪홀드', 'partial_sell': '🟡부분매도'})

            if 'source' in display.columns:
                display['source'] = display['source'].map({'scheduled': '🕐정기', 'triggered': '⚡긴급', 'stop_loss': '🛑손절', 'take_profit': '💰익절'}).fillna('🕐정기')

            if 'model' in display.columns:
                def format_model(m):
                    if pd.isna(m) or not m:
                        return "-"
                    if 'sonnet' in str(m).lower():
                        return '🟣Sonnet'
                    if 'haiku' in str(m).lower():
                        return '🟢Haiku'
                    if 'opus' in str(m).lower():
                        return '🔴Opus'
                    return str(m)[:10]
                display['model'] = display['model'].apply(format_model)

            display['btc_balance'] = display['btc_balance'].apply(lambda x: f"{x:.4f}")
            display['btc_krw_price'] = display['btc_krw_price'].apply(lambda x: f"{x:,.0f}")
            # reason 번역 적용 (전체 텍스트 유지)
            def format_reason(x):
                if pd.isna(x) or not x:
                    return "-"
                text = str(x)
                translated = translate_to_korean(text[:500])  # 더 긴 텍스트 허용
                return translated
            display['reason'] = display['reason'].apply(format_reason)

            col_names = {'timestamp': '시간', 'decision': '결정', 'percentage': '%', 'source': '출처', 'model': '모델', 'pnl_percentage': '손익', 'btc_balance': 'BTC', 'btc_krw_price': '가격', 'reason': '이유'}
            display.columns = [col_names.get(c, c) for c in display.columns]

            # column_config로 이유 컬럼 넓게 표시 (클릭 시 전체 내용 표시)
            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "이유": st.column_config.TextColumn(
                        "이유",
                        width="large",
                        help="클릭하면 전체 내용을 볼 수 있습니다"
                    )
                }
            )

    with tab2:
        if not orders_df.empty:
            ord_display = orders_df.copy()
            ord_display['created_at'] = ord_display['created_at'].dt.strftime('%m/%d %H:%M')
            ord_display['side'] = ord_display['side'].map({'bid': '🟢매수', 'ask': '🔴매도'})
            ord_display['price'] = ord_display['price'].apply(lambda x: f"₩{x:,.0f}" if pd.notna(x) else "-")
            ord_display['executed_volume'] = ord_display['executed_volume'].apply(lambda x: f"{x:.6f}")
            ord_display['paid_fee'] = ord_display['paid_fee'].apply(lambda x: f"₩{x:,.0f}" if pd.notna(x) else "-")
            st.dataframe(ord_display[['created_at', 'side', 'price', 'executed_volume', 'paid_fee']].head(20), use_container_width=True, hide_index=True, column_config={'created_at': '시간', 'side': '구분', 'price': '체결가', 'executed_volume': 'BTC', 'paid_fee': '수수료'})
        else:
            st.info("체결 내역 없음")

    with tab3:
        if not deposits_df.empty:
            dep = deposits_df.copy()
            dep['created_at'] = dep['created_at'].dt.strftime('%m/%d %H:%M')
            dep['type'] = dep['type'].map({'deposit': '🟢입금', 'withdraw': '🔴출금'})
            dep['amount'] = dep['amount'].apply(lambda x: f"₩{x:,.0f}")
            st.dataframe(dep[['created_at', 'type', 'amount', 'memo']].head(20), use_container_width=True, hide_index=True, column_config={'created_at': '시간', 'type': '유형', 'amount': '금액', 'memo': '메모'})
        else:
            st.info("입출금 기록 없음")

    with tab4:
        if not expenses_df.empty:
            exp = expenses_df.copy()
            exp['created_at'] = exp['created_at'].dt.strftime('%m/%d %H:%M')
            exp['category'] = exp['category'].map({'api': '🔴API', 'server': '🟢서버', 'other': '⚪기타'})
            exp['amount'] = exp['amount'].apply(lambda x: f"₩{x:,.0f}")
            st.dataframe(exp[['id', 'created_at', 'category', 'name', 'amount', 'period']].head(20), use_container_width=True, hide_index=True)
        else:
            st.info("비용 기록 없음")

    # 푸터
    st.divider()
    c1, c2 = st.columns(2)
    c1.caption(f"거래: {perf.get('total_trades', 0)}회 (매수 {perf.get('buy_count', 0)} / 매도 {perf.get('sell_count', 0)} / 홀드 {perf.get('hold_count', 0)})")
    c2.caption(f"🕐정기 {perf.get('scheduled_count', 0)} / ⚡긴급 {perf.get('triggered_count', 0)} / 🛑손절 {perf.get('stop_loss_count', 0)} / 💰익절 {perf.get('take_profit_count', 0)}")

# ============================================================================
# 미국 주식 대시보드
# ============================================================================

def render_us_stock_dashboard(days):
    """미국 주식 대시보드 렌더링"""

    # 시장 지수
    indices = get_market_indices()
    sectors = get_sector_performance()

    # 헤더 - 시장 지수
    st.markdown("### 📊 미국 주식 자동매매")

    if indices:
        cols = st.columns(len(indices))
        for i, (name, data) in enumerate(indices.items()):
            with cols[i]:
                if name == "VIX":
                    st.metric(name, f"{data['price']:.1f}", f"{data['change_pct']:+.2f}%", delta_color="inverse")
                else:
                    st.metric(name, f"{data['price']:,.0f}", f"{data['change_pct']:+.2f}%")

    # 포트폴리오 데이터
    portfolio_df = get_us_portfolio_snapshots(days)
    trades_df = get_us_stock_trades(days)
    deposits_df = get_us_stock_deposits()

    # 실질 수익 계산
    perf = calculate_us_stock_performance(portfolio_df, deposits_df, trades_df)

    # 포트폴리오 현황
    st.markdown("#### 포트폴리오 현황")

    if not portfolio_df.empty:
        latest = portfolio_df.iloc[0]

        # 투자 성과 (입출금 반영)
        st.markdown("##### 투자 성과")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("순입금", format_usd(perf.get('net_deposits', 0)))
        c2.metric("현재 총자산", format_usd(perf.get('current_total', 0)))
        c3.metric("실질수익", format_usd(perf.get('real_profit', 0)), f"{perf.get('real_rate', 0):+.2f}%")
        c4.metric("실현손익", format_usd(perf.get('realized_pnl', 0)))
        c5.metric("미실현손익", format_usd(perf.get('unrealized_pnl', 0)))

        # 자산 현황
        st.markdown("##### 자산 현황")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 자산", format_usd(latest.get('total_value', 0)))
        c2.metric("현금", format_usd(latest.get('cash', 0)), f"{latest.get('cash_ratio', 0)*100:.1f}%")
        c3.metric("투자금", format_usd(latest.get('invested', 0)))
        c4.metric("미실현 손익", format_usd(latest.get('unrealized_pnl', 0)), f"{latest.get('unrealized_pnl_pct', 0)*100:+.2f}%")

        # 보유 종목
        positions = latest.get('positions')
        if positions and isinstance(positions, dict):
            st.markdown("#### 보유 종목")
            pos_data = []
            for symbol, pos in positions.items():
                if isinstance(pos, dict):
                    pos_data.append({
                        '종목': symbol,
                        '수량': pos.get('quantity', 0),
                        '평균단가': f"${pos.get('avg_price', 0):.2f}",
                        '현재가': f"${pos.get('current_price', 0):.2f}",
                        '손익': f"${pos.get('unrealized_pnl', 0):+.2f}",
                        '수익률': f"{pos.get('unrealized_pnl_pct', 0)*100:+.2f}%",
                    })
            if pos_data:
                st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)
    else:
        st.info("포트폴리오 데이터가 없습니다. 자동매매 시스템이 실행되면 데이터가 표시됩니다.")

        # 데모 데이터 표시
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 자산", "$0.00")
        c2.metric("현금", "$0.00", "0%")
        c3.metric("투자금", "$0.00")
        c4.metric("미실현 손익", "$0.00", "0%")

    # 차트
    st.markdown("#### 차트")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("포트폴리오 추이")
        st.plotly_chart(create_us_portfolio_chart(portfolio_df), use_container_width=True, config={'displayModeBar': False}, key="us_portfolio_chart")
    with c2:
        st.caption("미실현 손익 추이")
        st.plotly_chart(create_us_pnl_chart(portfolio_df), use_container_width=True, config={'displayModeBar': False}, key="us_pnl_chart")

    c1, c2 = st.columns(2)
    with c1:
        st.caption("섹터 성과 (전일 대비)")
        st.plotly_chart(create_sector_chart(sectors), use_container_width=True, config={'displayModeBar': False}, key="us_sector_chart")
    with c2:
        st.caption("거래 유형")
        st.plotly_chart(create_us_trade_decision_chart(trades_df), use_container_width=True, config={'displayModeBar': False}, key="us_trade_decision_chart")

    # 기록 탭
    st.markdown("#### 기록")
    us_tab1, us_tab2 = st.tabs(["거래", "입출금"])

    with us_tab1:
        if not trades_df.empty:
            page_size = 15
            total_records = len(trades_df)
            total_pages = max(1, (total_records + page_size - 1) // page_size)

            if 'us_trades_page' not in st.session_state:
                st.session_state.us_trades_page = 1

            col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
            with col1:
                if st.button('⏮️', key='us_first'):
                    st.session_state.us_trades_page = 1
            with col2:
                if st.button('◀️', key='us_prev'):
                    if st.session_state.us_trades_page > 1:
                        st.session_state.us_trades_page -= 1
            with col3:
                st.markdown(f"<p style='text-align:center; margin-top:8px;'>{st.session_state.us_trades_page} / {total_pages}</p>", unsafe_allow_html=True)
            with col4:
                if st.button('▶️', key='us_next'):
                    if st.session_state.us_trades_page < total_pages:
                        st.session_state.us_trades_page += 1
            with col5:
                if st.button('⏭️', key='us_last'):
                    st.session_state.us_trades_page = total_pages

            start_idx = (st.session_state.us_trades_page - 1) * page_size
            end_idx = start_idx + page_size
            page_data = trades_df.iloc[start_idx:end_idx].copy()

            # 컬럼 선택
            display_cols = ['created_at', 'symbol', 'action', 'quantity', 'price', 'amount']
            if 'pnl' in page_data.columns:
                display_cols.append('pnl')
            if 'model' in page_data.columns:
                display_cols.append('model')
            if 'key_reasons' in page_data.columns:
                display_cols.append('key_reasons')

            display = page_data[[c for c in display_cols if c in page_data.columns]].copy()
            display['created_at'] = display['created_at'].dt.strftime('%m/%d %H:%M')

            if 'action' in display.columns:
                display['action'] = display['action'].map({'buy': '🟢매수', 'sell': '🔴매도', 'stop_loss': '🛑손절', 'take_profit': '💰익절'})

            if 'price' in display.columns:
                display['price'] = display['price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "-")
            if 'amount' in display.columns:
                display['amount'] = display['amount'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "-")
            if 'pnl' in display.columns:
                display['pnl'] = display['pnl'].apply(lambda x: f"${x:+.2f}" if pd.notna(x) else "-")

            if 'model' in display.columns:
                def format_model(m):
                    if pd.isna(m) or not m:
                        return "-"
                    if 'sonnet' in str(m).lower():
                        return '🟣Sonnet'
                    if 'haiku' in str(m).lower():
                        return '🟢Haiku'
                    return str(m)[:10]
                display['model'] = display['model'].apply(format_model)

            # key_reasons 포맷팅 (리스트 → 문자열)
            if 'key_reasons' in display.columns:
                def format_reasons(x):
                    if pd.isna(x) or not x:
                        return "-"
                    if isinstance(x, list):
                        return " | ".join(x[:3])  # 상위 3개만
                    return str(x)
                display['key_reasons'] = display['key_reasons'].apply(format_reasons)

            col_names = {'created_at': '시간', 'symbol': '종목', 'action': '거래', 'quantity': '수량', 'price': '가격', 'amount': '금액', 'pnl': '손익', 'model': '모델', 'key_reasons': '이유'}
            display.columns = [col_names.get(c, c) for c in display.columns]

            # column_config로 이유 컬럼 넓게 표시
            column_cfg = {}
            if '이유' in display.columns:
                column_cfg["이유"] = st.column_config.TextColumn("이유", width="large")

            st.dataframe(display, use_container_width=True, hide_index=True, height=400, column_config=column_cfg if column_cfg else None)
        else:
            st.info("거래 기록이 없습니다.")

    with us_tab2:
        if not deposits_df.empty:
            dep = deposits_df.copy()
            dep['created_at'] = dep['created_at'].dt.strftime('%m/%d %H:%M')
            dep['type'] = dep['type'].map({'deposit': '🟢입금', 'withdraw': '🔴출금'})
            dep['amount'] = dep['amount'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(dep[['created_at', 'type', 'amount', 'memo']].head(20), use_container_width=True, hide_index=True, column_config={'created_at': '시간', 'type': '유형', 'amount': '금액', 'memo': '메모'})
        else:
            st.info("입출금 기록 없음. 설정에서 초기 입금액을 추가하세요.")

    # 푸터
    st.divider()
    buy_count = len(trades_df[trades_df['action'] == 'buy']) if not trades_df.empty and 'action' in trades_df.columns else 0
    sell_count = len(trades_df[trades_df['action'] == 'sell']) if not trades_df.empty and 'action' in trades_df.columns else 0
    st.caption(f"거래: {len(trades_df)}회 (매수 {buy_count} / 매도 {sell_count}) | 업데이트: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')} KST")

# ============================================================================
# 메인 앱
# ============================================================================

def main():
    st.set_page_config(page_title="JWCoin Dashboard", page_icon="📈", layout="wide")

    # CSS
    st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    .block-container { padding: 1rem 2rem; max-width: 100%; }
    h1 { font-size: 1.5rem !important; font-weight: 600 !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.1rem !important; font-weight: 500 !important; margin: 1rem 0 0.5rem 0 !important; }
    h3 { font-size: 1rem !important; font-weight: 500 !important; }
    [data-testid="stMetric"] { border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 0.8rem; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem; }
    [data-testid="stMetricValue"] { font-size: 1.1rem; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 16px; font-size: 0.85rem; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    .stButton > button { border-radius: 8px; font-size: 0.85rem; padding: 0.4rem 1rem; }
    hr { margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

    # 헤더
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("📈 JWCoin Dashboard")
    with col2:
        days = st.selectbox("조회 기간", [7, 14, 30, 60, 90], index=2, format_func=lambda x: f"{x}일")
    with col3:
        if st.button("🔄 새로고침"):
            st.cache_data.clear()
            st.rerun()

    # 메인 탭 - 코인 / 미국 주식
    main_tab1, main_tab2 = st.tabs(["🪙 비트코인", "🇺🇸 미국 주식"])

    with main_tab1:
        # 코인 전용 설정
        with st.expander("⚙️ 코인 설정", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                chart_start_date = st.date_input(
                    "차트 시작일",
                    value=datetime.now(KST) - timedelta(days=7),
                    max_value=datetime.now(KST).date(),
                    key="coin_chart_date"
                )
            with col2:
                st.empty()

            st.divider()

            # 입출금 & 비용 추가
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**💵 입출금 수동 추가**")
                dep_col1, dep_col2 = st.columns(2)
                with dep_col1:
                    dep_type = st.selectbox("유형", ["deposit", "withdraw"], format_func=lambda x: "입금" if x == "deposit" else "출금", key="dep_type")
                    dep_amt = st.number_input("금액", min_value=0, step=10000, key="dep_amt")
                with dep_col2:
                    dep_memo = st.text_input("메모", key="dep_memo")
                    if st.button("입출금 추가", key="add_dep"):
                        if dep_amt > 0 and add_deposit(dep_amt, dep_type, dep_memo):
                            st.success("완료")
                            st.cache_data.clear()
                            st.rerun()

            with col2:
                st.markdown("**💸 비용 수동 추가**")
                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    exp_cat = st.selectbox("카테고리", ["api", "server", "other"], format_func=lambda x: {"api": "API", "server": "서버", "other": "기타"}[x], key="exp_cat")
                    exp_name = st.text_input("항목명", key="exp_name")
                    exp_amt = st.number_input("금액 (원)", min_value=0, step=1000, key="exp_amt")
                with exp_col2:
                    exp_period = st.selectbox("주기", ["monthly", "daily", "yearly"], format_func=lambda x: {"monthly": "월", "daily": "일", "yearly": "연"}[x], key="exp_period")
                    exp_memo = st.text_input("메모 (선택)", key="exp_memo")
                    if st.button("비용 추가", key="add_exp"):
                        if exp_amt > 0 and exp_name and add_expense(exp_cat, exp_name, exp_amt, exp_period, exp_memo):
                            st.success("완료")
                            st.cache_data.clear()
                            st.rerun()

        render_coin_dashboard(days, chart_start_date)

    with main_tab2:
        # 미국 주식 설정
        with st.expander("⚙️ 미국 주식 설정", expanded=False):
            st.markdown("**💵 입출금 수동 추가 (USD)**")
            us_col1, us_col2, us_col3 = st.columns(3)
            with us_col1:
                us_dep_type = st.selectbox("유형", ["deposit", "withdraw"], format_func=lambda x: "입금" if x == "deposit" else "출금", key="us_dep_type")
            with us_col2:
                us_dep_amt = st.number_input("금액 ($)", min_value=0.0, step=100.0, key="us_dep_amt")
            with us_col3:
                us_dep_memo = st.text_input("메모", key="us_dep_memo")

            if st.button("입출금 추가", key="us_add_dep"):
                if us_dep_amt > 0 and add_us_stock_deposit(us_dep_amt, us_dep_type, us_dep_memo):
                    st.success("완료")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("입출금 추가 실패")

        render_us_stock_dashboard(days)

if __name__ == "__main__":
    main()
