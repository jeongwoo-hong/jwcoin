import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pyupbit
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

# 환경변수 로드
load_dotenv()

# Supabase 연결
@st.cache_resource
def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("Supabase 설정이 없습니다.")
        return None
    return create_client(url, key)

# Supabase에서 거래 기록 조회
@st.cache_data(ttl=60)
def get_trades_from_supabase(days=30):
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()

    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        response = supabase.table("trades") \
            .select("*") \
            .gte("timestamp", cutoff) \
            .order("timestamp", desc=True) \
            .execute()

        if response.data:
            df = pd.DataFrame(response.data)
            # UTC -> KST 변환
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        return pd.DataFrame()

# 현재 BTC 가격
@st.cache_data(ttl=30)
def get_current_btc_price():
    try:
        return pyupbit.get_current_price("KRW-BTC")
    except:
        return None

# 숫자 포맷팅
def format_number(value):
    if pd.isna(value) or value is None:
        return "0"
    try:
        num = float(value)
        if abs(num) >= 1_000_000_000:
            return f"{num/1_000_000_000:.2f}B"
        elif abs(num) >= 1_000_000:
            return f"{num/1_000_000:.2f}M"
        elif abs(num) >= 1_000:
            return f"{num/1_000:.1f}K"
        elif 0 < abs(num) < 1:
            return f"{num:.6f}"
        else:
            return f"{num:,.0f}"
    except:
        return str(value)

# 성과 계산
def calculate_performance(df):
    if df.empty or len(df) < 2:
        return {}

    # 시간순 정렬 (오래된 것 먼저)
    df_sorted = df.sort_values('timestamp')

    # 첫 번째와 마지막 기록
    first = df_sorted.iloc[0]
    last = df_sorted.iloc[-1]

    # 초기/최종 자산
    initial_asset = first['krw_balance'] + first['btc_balance'] * first['btc_krw_price']
    final_asset = last['krw_balance'] + last['btc_balance'] * last['btc_krw_price']

    # 수익률
    profit = final_asset - initial_asset
    profit_rate = (profit / initial_asset * 100) if initial_asset > 0 else 0

    # 거래 통계
    total_trades = len(df)
    buy_count = len(df[df['decision'] == 'buy'])
    sell_count = len(df[df['decision'] == 'sell'])
    hold_count = len(df[df['decision'] == 'hold'])

    return {
        'initial_asset': initial_asset,
        'final_asset': final_asset,
        'profit': profit,
        'profit_rate': profit_rate,
        'total_trades': total_trades,
        'buy_count': buy_count,
        'sell_count': sell_count,
        'hold_count': hold_count
    }

# 자산 추이 차트
def create_asset_chart(df):
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values('timestamp')
    df_sorted['total_asset'] = df_sorted['krw_balance'] + df_sorted['btc_balance'] * df_sorted['btc_krw_price']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'],
        y=df_sorted['total_asset'],
        mode='lines+markers',
        name='총 자산',
        line=dict(color='#00D4AA', width=2),
        marker=dict(size=6)
    ))

    fig.update_layout(
        title='총 자산 추이',
        xaxis_title='시간',
        yaxis_title='자산 (KRW)',
        height=400,
        template='plotly_dark'
    )

    return fig

# 거래 결정 분포 차트
def create_decision_chart(df):
    if df.empty:
        return go.Figure()

    decision_counts = df['decision'].value_counts()
    colors = {'buy': '#00D4AA', 'sell': '#FF6B6B', 'hold': '#4ECDC4'}

    fig = go.Figure(data=[go.Pie(
        labels=decision_counts.index,
        values=decision_counts.values,
        marker_colors=[colors.get(d, '#888') for d in decision_counts.index],
        hole=0.4
    )])

    fig.update_layout(
        title='거래 결정 분포',
        height=300,
        template='plotly_dark'
    )

    return fig

# BTC 보유량 추이 차트
def create_btc_chart(df):
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values('timestamp')

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'],
        y=df_sorted['btc_balance'],
        mode='lines+markers',
        name='BTC 보유량',
        line=dict(color='#F7931A', width=2),
        fill='tozeroy',
        fillcolor='rgba(247, 147, 26, 0.2)'
    ))

    fig.update_layout(
        title='BTC 보유량 추이',
        xaxis_title='시간',
        yaxis_title='BTC',
        height=300,
        template='plotly_dark'
    )

    return fig

# 메인
def main():
    st.set_page_config(
        page_title="JWCoin Trading Dashboard",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 디버그: 환경변수 확인
    import os
    st.sidebar.write(f"PORT: {os.getenv('PORT', 'not set')}")
    st.sidebar.write(f"SUPABASE_URL: {'set' if os.getenv('SUPABASE_URL') else 'not set'}")
    st.sidebar.write(f"SUPABASE_KEY: {'set' if os.getenv('SUPABASE_KEY') else 'not set'}")

    # 커스텀 CSS
    st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .stMetric { background-color: #1E2130; padding: 15px; border-radius: 10px; }
    .stMetric label { color: #888; }
    .stMetric [data-testid="stMetricValue"] { color: #fff; font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

    # 사이드바
    st.sidebar.title("⚙️ 설정")
    days = st.sidebar.slider("조회 기간 (일)", 1, 90, 30)

    if st.sidebar.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

    # 헤더
    st.title("📈 JWCoin Trading Dashboard")
    st.markdown("AI 자동매매 성과 모니터링")

    # 데이터 로드
    with st.spinner("데이터 로딩 중..."):
        trades_df = get_trades_from_supabase(days)
        current_price = get_current_btc_price()

    if trades_df.empty:
        st.warning("거래 기록이 없습니다.")
        st.stop()

    # 성과 계산
    perf = calculate_performance(trades_df)

    # 현재 상태
    st.header("💰 현재 상태")

    latest = trades_df.iloc[0]  # 가장 최근 기록
    current_btc_value = latest['btc_balance'] * (current_price or latest['btc_krw_price'])
    current_total = latest['krw_balance'] + current_btc_value

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("보유 BTC", f"{latest['btc_balance']:.6f} BTC")
    with col2:
        st.metric("BTC 가치", f"{format_number(current_btc_value)} KRW")
    with col3:
        st.metric("보유 KRW", f"{format_number(latest['krw_balance'])} KRW")
    with col4:
        st.metric("총 자산", f"{format_number(current_total)} KRW")

    # 성과 지표
    st.header("📊 성과 분석")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        profit_color = "normal" if perf.get('profit', 0) >= 0 else "inverse"
        st.metric(
            "총 수익",
            f"{format_number(perf.get('profit', 0))} KRW",
            delta=f"{perf.get('profit_rate', 0):.2f}%"
        )
    with col2:
        st.metric("총 거래 횟수", f"{perf.get('total_trades', 0)}회")
    with col3:
        st.metric("매수/매도", f"{perf.get('buy_count', 0)} / {perf.get('sell_count', 0)}")
    with col4:
        st.metric("홀드", f"{perf.get('hold_count', 0)}회")

    # 차트
    st.header("📈 차트")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.plotly_chart(create_asset_chart(trades_df), use_container_width=True)
    with col2:
        st.plotly_chart(create_decision_chart(trades_df), use_container_width=True)

    st.plotly_chart(create_btc_chart(trades_df), use_container_width=True)

    # 최근 거래 기록
    st.header("📜 최근 거래 기록")

    display_df = trades_df[['timestamp', 'decision', 'percentage', 'btc_balance', 'krw_balance', 'btc_krw_price', 'reason']].head(20).copy()
    display_df.columns = ['시간', '결정', '비율(%)', 'BTC 잔고', 'KRW 잔고', 'BTC 가격', '이유']
    display_df['시간'] = display_df['시간'].dt.strftime('%Y-%m-%d %H:%M (KST)')
    display_df['결정'] = display_df['결정'].map({'buy': '🟢 매수', 'sell': '🔴 매도', 'hold': '⚪ 홀드'})
    display_df['BTC 잔고'] = display_df['BTC 잔고'].apply(lambda x: f"{x:.6f}")
    display_df['KRW 잔고'] = display_df['KRW 잔고'].apply(lambda x: f"{x:,.0f}")
    display_df['BTC 가격'] = display_df['BTC 가격'].apply(lambda x: f"{x:,.0f}")
    display_df['이유'] = display_df['이유'].apply(lambda x: x[:100] + '...' if len(str(x)) > 100 else x)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # AI 분석 (최근 반성)
    if 'reflection' in trades_df.columns:
        st.header("🤖 AI 분석")
        latest_reflection = trades_df.iloc[0].get('reflection', '')
        if latest_reflection:
            st.markdown(f"> {latest_reflection}")

    # 푸터
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"현재 BTC 가격: {current_price:,.0f} KRW" if current_price else "BTC 가격 조회 실패")
    with col2:
        kst_now = datetime.now(KST)
        st.caption(f"마지막 업데이트: {kst_now.strftime('%Y-%m-%d %H:%M:%S')} (KST)")

if __name__ == "__main__":
    main()