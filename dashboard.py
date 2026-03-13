import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pyupbit
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
# 데이터 조회 함수들
# ============================================================================

@st.cache_resource
def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

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

# ============================================================================
# 데이터 조작 함수들
# ============================================================================

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
# 계산 함수들
# ============================================================================

def format_krw(value):
    if pd.isna(value) or value is None:
        return "0"
    try:
        return f"{float(value):,.0f}"
    except:
        return str(value)

def calculate_monthly_expenses(expenses_df, days=30):
    if expenses_df.empty:
        return 0, {}
    total = 0
    by_cat = {'api': 0, 'server': 0, 'other': 0}
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

def calculate_performance(trades_df, deposits_df, expenses_df, current_btc_price, days=30):
    if trades_df.empty or len(trades_df) < 2:
        return {}
    df_sorted = trades_df.sort_values('timestamp')
    first, last = df_sorted.iloc[0], df_sorted.iloc[-1]

    # 현재 BTC 가격으로 통일
    price = current_btc_price or last['btc_krw_price']
    initial = first['krw_balance'] + first['btc_balance'] * price
    final = last['krw_balance'] + last['btc_balance'] * price

    total_dep = deposits_df[deposits_df['type'] == 'deposit']['amount'].sum() if not deposits_df.empty else 0
    total_wd = deposits_df[deposits_df['type'] == 'withdraw']['amount'].sum() if not deposits_df.empty else 0
    net_dep = total_dep - total_wd

    monthly_exp, exp_by_cat = calculate_monthly_expenses(expenses_df, days)

    trading_profit = (final - initial) - net_dep
    invested = initial + net_dep
    trading_rate = (trading_profit / invested * 100) if invested > 0 else 0
    real_profit = trading_profit - monthly_exp
    real_rate = (real_profit / invested * 100) if invested > 0 else 0

    return {
        'initial': initial, 'final': final,
        'total_deposits': total_dep, 'total_withdrawals': total_wd, 'net_deposits': net_dep,
        'trading_profit': trading_profit, 'trading_rate': trading_rate,
        'monthly_expenses': monthly_exp, 'expenses_by_cat': exp_by_cat,
        'real_profit': real_profit, 'real_rate': real_rate,
        'total_trades': len(trades_df),
        'buy_count': len(trades_df[trades_df['decision'] == 'buy']),
        'sell_count': len(trades_df[trades_df['decision'] == 'sell']),
        'hold_count': len(trades_df[trades_df['decision'] == 'hold']),
        # 출처별 통계 (source 컬럼이 있는 경우)
        'scheduled_count': len(trades_df[trades_df['source'] == 'scheduled']) if 'source' in trades_df.columns else 0,
        'triggered_count': len(trades_df[trades_df['source'] == 'triggered']) if 'source' in trades_df.columns else 0,
        'stop_loss_count': len(trades_df[trades_df['source'] == 'stop_loss']) if 'source' in trades_df.columns else 0,
        'take_profit_count': len(trades_df[trades_df['source'] == 'take_profit']) if 'source' in trades_df.columns else 0
    }

# ============================================================================
# 차트 함수들
# ============================================================================

def create_asset_chart(df):
    if df.empty:
        return go.Figure()
    df_sorted = df.sort_values('timestamp').copy()
    df_sorted['total'] = df_sorted['krw_balance'] + df_sorted['btc_balance'] * df_sorted['btc_krw_price']
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['total'],
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
    labels_map = {'api': 'API', 'server': '서버', 'other': '기타'}
    colors_map = {'api': '#FF6B6B', 'server': '#4ECDC4', 'other': '#95A5A6'}
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
# 메인 앱
# ============================================================================

def main():
    st.set_page_config(page_title="JWCoin Dashboard", page_icon="📈", layout="wide")

    # CSS (테마는 .streamlit/config.toml에서 설정)
    st.markdown("""
    <style>
    /* 헤더 숨김 */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* 레이아웃 */
    .block-container { padding: 1rem 2rem; max-width: 100%; }

    /* 제목 크기 */
    h1 { font-size: 1.5rem !important; font-weight: 600 !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.1rem !important; font-weight: 500 !important; margin: 1rem 0 0.5rem 0 !important; }
    h3 { font-size: 1rem !important; font-weight: 500 !important; }

    /* 메트릭 카드 */
    [data-testid="stMetric"] {
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"] { font-size: 0.75rem; }
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-weight: 600; }

    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 16px; font-size: 0.85rem; }

    /* 데이터프레임 */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* 버튼 */
    .stButton > button { border-radius: 8px; font-size: 0.85rem; padding: 0.4rem 1rem; }

    /* 구분선 */
    hr { margin: 1rem 0; }

    /* Expander */
    .streamlit-expanderHeader { font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

    # ===== 사이드바 =====
    with st.sidebar:
        st.title("⚙️ 설정")
        days = st.slider("조회 기간", 1, 90, 30, format="%d일")

        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        # 입출금
        st.markdown("##### 💵 입출금")
        st.caption("업비트는 자동 조회")
        with st.expander("수동 추가"):
            dep_type = st.selectbox("유형", ["deposit", "withdraw"], format_func=lambda x: "입금" if x == "deposit" else "출금", key="dep_type")
            dep_amt = st.number_input("금액", min_value=0, step=10000, key="dep_amt")
            dep_memo = st.text_input("메모", key="dep_memo")
            if st.button("추가", key="add_dep", use_container_width=True):
                if dep_amt > 0 and add_deposit(dep_amt, dep_type, dep_memo):
                    st.success("완료")
                    st.cache_data.clear()
                    st.rerun()

        st.divider()

        # 비용
        st.markdown("##### 💸 운영 비용")
        with st.expander("비용 추가"):
            exp_cat = st.selectbox("카테고리", ["api", "server", "other"], format_func=lambda x: {"api": "API", "server": "서버", "other": "기타"}[x], key="exp_cat")
            exp_name = st.text_input("항목명", key="exp_name")
            exp_amt = st.number_input("금액", min_value=0, step=1000, key="exp_amt")
            exp_period = st.selectbox("주기", ["monthly", "daily", "yearly", "one-time"], format_func=lambda x: {"monthly": "월", "daily": "일", "yearly": "연", "one-time": "1회"}[x], key="exp_period")
            if st.button("추가", key="add_exp", use_container_width=True):
                if exp_amt > 0 and exp_name and add_expense(exp_cat, exp_name, exp_amt, exp_period, ""):
                    st.success("완료")
                    st.cache_data.clear()
                    st.rerun()

    # ===== 데이터 로드 =====
    trades_df = get_trades_from_supabase(days)
    deposits_df = get_all_deposits()
    expenses_df = get_expenses()
    btc_price = get_current_btc_price()

    # ===== 헤더 =====
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📈 JWCoin Dashboard")
    with col2:
        if btc_price:
            st.metric("BTC", f"₩{format_krw(btc_price)}")

    if trades_df.empty:
        st.warning("거래 기록이 없습니다.")
        st.stop()

    # 성과 계산 (현재 BTC 가격 기준)
    perf = calculate_performance(trades_df, deposits_df, expenses_df, btc_price, days)
    latest = trades_df.iloc[0]
    btc_val = latest['btc_balance'] * (btc_price or latest['btc_krw_price'])
    total_asset = latest['krw_balance'] + btc_val

    # ===== 현재 자산 =====
    st.markdown("## 💰 현재 자산")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BTC 보유", f"{latest['btc_balance']:.6f}")
    c2.metric("BTC 가치", f"₩{format_krw(btc_val)}")
    c3.metric("KRW 보유", f"₩{format_krw(latest['krw_balance'])}")
    c4.metric("총 자산", f"₩{format_krw(total_asset)}")

    # ===== 투자 성과 =====
    st.markdown("## 📊 투자 성과")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("입금", f"₩{format_krw(perf.get('total_deposits', 0))}")
    c2.metric("출금", f"₩{format_krw(perf.get('total_withdrawals', 0))}")
    c3.metric("투자수익", f"₩{format_krw(perf.get('trading_profit', 0))}", f"{perf.get('trading_rate', 0):+.2f}%")
    c4.metric("운영비용", f"₩{format_krw(perf.get('monthly_expenses', 0))}/월")
    c5.metric("실질수익", f"₩{format_krw(perf.get('real_profit', 0))}", f"{perf.get('real_rate', 0):+.2f}%")

    # ===== 차트 =====
    st.markdown("## 📈 차트")

    # 상단: 자산 추이
    st.plotly_chart(create_asset_chart(trades_df), use_container_width=True, config={'displayModeBar': False})

    # 하단: 3개 차트
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

    # ===== 기록 탭 =====
    st.markdown("## 📋 기록")
    tab1, tab2, tab3 = st.tabs(["거래", "입출금", "비용"])

    with tab1:
        if not trades_df.empty:
            # 기본 컬럼
            cols = ['timestamp', 'decision', 'percentage']

            # source 컬럼이 있으면 추가
            if 'source' in trades_df.columns:
                cols.append('source')

            # pnl_percentage 컬럼이 있으면 추가
            if 'pnl_percentage' in trades_df.columns:
                cols.append('pnl_percentage')

            cols.extend(['btc_balance', 'btc_krw_price', 'reason'])

            # trigger_reason이 있으면 추가
            if 'trigger_reason' in trades_df.columns:
                cols.append('trigger_reason')

            display = trades_df[[c for c in cols if c in trades_df.columns]].head(20).copy()
            display['timestamp'] = display['timestamp'].dt.strftime('%m/%d %H:%M')
            display['decision'] = display['decision'].map({'buy': '🟢매수', 'sell': '🔴매도', 'hold': '⚪홀드', 'partial_sell': '🟡부분매도'})

            # source 포맷팅
            if 'source' in display.columns:
                display['source'] = display['source'].map({
                    'scheduled': '🕐정기',
                    'triggered': '⚡긴급',
                    'stop_loss': '🛑손절',
                    'take_profit': '💰익절'
                }).fillna('🕐정기')

            # pnl_percentage 포맷팅
            if 'pnl_percentage' in display.columns:
                display['pnl_percentage'] = display['pnl_percentage'].apply(
                    lambda x: f"{x*100:+.1f}%" if pd.notna(x) and x != 0 else "-"
                )

            display['btc_balance'] = display['btc_balance'].apply(lambda x: f"{x:.4f}")
            display['btc_krw_price'] = display['btc_krw_price'].apply(lambda x: f"{x:,.0f}")
            display['reason'] = display['reason'].apply(lambda x: str(x)[:40] + '...' if len(str(x)) > 40 else x)

            # trigger_reason 포맷팅
            if 'trigger_reason' in display.columns:
                display['trigger_reason'] = display['trigger_reason'].apply(
                    lambda x: str(x)[:30] + '...' if pd.notna(x) and len(str(x)) > 30 else (x if pd.notna(x) else "-")
                )

            # 컬럼명 변경
            col_names = {
                'timestamp': '시간', 'decision': '결정', 'percentage': '%',
                'source': '출처', 'pnl_percentage': '손익',
                'btc_balance': 'BTC', 'btc_krw_price': '가격',
                'reason': '이유', 'trigger_reason': '트리거'
            }
            display.columns = [col_names.get(c, c) for c in display.columns]

            st.dataframe(display, use_container_width=True, hide_index=True, height=450)

            # 번역
            with st.expander("🌐 번역"):
                idx = st.selectbox("거래 선택", range(min(20, len(trades_df))), format_func=lambda i: f"{trades_df.iloc[i]['timestamp'].strftime('%m/%d %H:%M')} - {trades_df.iloc[i]['decision']}")
                if st.button("번역", key="tr_reason"):
                    with st.spinner("번역 중..."):
                        st.success(translate_to_korean(trades_df.iloc[idx]['reason']))

    with tab2:
        if not deposits_df.empty:
            dep = deposits_df.copy()
            dep['created_at'] = dep['created_at'].dt.strftime('%m/%d %H:%M')
            dep['type'] = dep['type'].map({'deposit': '🟢입금', 'withdraw': '🔴출금'})
            dep['amount'] = dep['amount'].apply(lambda x: f"₩{x:,.0f}")
            dep['source'] = dep['memo'].apply(lambda x: '업비트' if '업비트' in str(x) else '수동')
            st.dataframe(dep[['created_at', 'type', 'amount', 'source', 'memo']], use_container_width=True, hide_index=True, column_config={'created_at': '시간', 'type': '유형', 'amount': '금액', 'source': '출처', 'memo': '메모'})

            manual = get_manual_deposits()
            if not manual.empty:
                with st.expander("수동 입력 삭제"):
                    del_id = st.number_input("삭제 ID", min_value=1, step=1, key="del_dep")
                    if st.button("삭제", key="del_dep_btn"):
                        if delete_deposit(del_id):
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.info("입출금 기록 없음")

    with tab3:
        if not expenses_df.empty:
            exp = expenses_df.copy()
            exp['created_at'] = exp['created_at'].dt.strftime('%m/%d %H:%M')
            exp['category'] = exp['category'].map({'api': '🔴API', 'server': '🟢서버', 'other': '⚪기타'})
            exp['period'] = exp['period'].map({'monthly': '월', 'daily': '일', 'yearly': '연', 'one-time': '1회'})
            exp['amount'] = exp['amount'].apply(lambda x: f"₩{x:,.0f}")
            st.dataframe(exp[['id', 'created_at', 'category', 'name', 'amount', 'period']], use_container_width=True, hide_index=True, column_config={'id': 'ID', 'created_at': '등록', 'category': '분류', 'name': '항목', 'amount': '금액', 'period': '주기'})

            with st.expander("비용 삭제"):
                del_id = st.number_input("삭제 ID", min_value=1, step=1, key="del_exp")
                if st.button("삭제", key="del_exp_btn"):
                    if delete_expense(del_id):
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("비용 기록 없음")

    # ===== AI 분석 =====
    if 'reflection' in trades_df.columns and trades_df.iloc[0].get('reflection'):
        st.markdown("## 🤖 AI 분석")
        reflection = trades_df.iloc[0]['reflection']
        st.caption(reflection[:200] + '...' if len(reflection) > 200 else reflection)
        if st.button("전체 보기 & 번역", key="tr_ref"):
            st.info(reflection)
            with st.spinner("번역 중..."):
                st.success(translate_to_korean(reflection))

    # ===== 푸터 =====
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.caption(f"거래: {perf.get('total_trades', 0)}회 (매수 {perf.get('buy_count', 0)} / 매도 {perf.get('sell_count', 0)} / 홀드 {perf.get('hold_count', 0)})")
    c2.caption(f"🕐정기 {perf.get('scheduled_count', 0)} / ⚡긴급 {perf.get('triggered_count', 0)} / 🛑손절 {perf.get('stop_loss_count', 0)} / 💰익절 {perf.get('take_profit_count', 0)}")
    c3.caption(f"업데이트: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')} KST")

if __name__ == "__main__":
    main()