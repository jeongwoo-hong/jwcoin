import streamlit as st
import pandas as pd
import plotly.express as px
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
            ts = pd.to_datetime(df['timestamp'])
            if ts.dt.tz is None:
                df['timestamp'] = ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            else:
                df['timestamp'] = ts.dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"거래 데이터 조회 실패: {e}")
        return pd.DataFrame()

# 입출금 기록 조회
@st.cache_data(ttl=60)
def get_deposits_from_supabase():
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()

    try:
        response = supabase.table("deposits") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()

        if response.data:
            df = pd.DataFrame(response.data)
            ts = pd.to_datetime(df['created_at'])
            if ts.dt.tz is None:
                df['created_at'] = ts.dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
            else:
                df['created_at'] = ts.dt.tz_convert('Asia/Seoul')
            return df
        return pd.DataFrame()
    except Exception as e:
        # 테이블이 없을 수 있음
        return pd.DataFrame()

# 입출금 기록 추가
def add_deposit(amount, deposit_type, memo):
    supabase = get_supabase_client()
    if not supabase:
        return False

    try:
        data = {
            "amount": float(amount),
            "type": deposit_type,
            "memo": memo
        }
        supabase.table("deposits").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"입출금 기록 추가 실패: {e}")
        return False

# 입출금 기록 삭제
def delete_deposit(deposit_id):
    supabase = get_supabase_client()
    if not supabase:
        return False

    try:
        supabase.table("deposits").delete().eq("id", deposit_id).execute()
        return True
    except Exception as e:
        st.error(f"삭제 실패: {e}")
        return False

# 현재 BTC 가격
@st.cache_data(ttl=30)
def get_current_btc_price():
    try:
        return pyupbit.get_current_price("KRW-BTC")
    except:
        return None

# 번역 함수
@st.cache_data(ttl=3600)
def translate_to_korean(text):
    if not text or pd.isna(text):
        return ""
    try:
        translator = GoogleTranslator(source='en', target='ko')
        # 긴 텍스트는 분할 번역
        if len(text) > 4500:
            text = text[:4500]
        return translator.translate(text)
    except Exception as e:
        return f"번역 실패: {e}"

# 숫자 포맷팅 (KRW: 천 단위 콤마, 1원 단위까지)
def format_krw(value):
    if pd.isna(value) or value is None:
        return "0"
    try:
        num = float(value)
        return f"{num:,.0f}"
    except:
        return str(value)

# 성과 계산 (입금액 제외)
def calculate_performance(trades_df, deposits_df):
    if trades_df.empty or len(trades_df) < 2:
        return {}

    # 시간순 정렬
    df_sorted = trades_df.sort_values('timestamp')
    first = df_sorted.iloc[0]
    last = df_sorted.iloc[-1]

    # 초기/최종 자산
    initial_asset = first['krw_balance'] + first['btc_balance'] * first['btc_krw_price']
    final_asset = last['krw_balance'] + last['btc_balance'] * last['btc_krw_price']

    # 총 입금/출금액 계산
    total_deposits = 0
    total_withdrawals = 0
    if not deposits_df.empty:
        total_deposits = deposits_df[deposits_df['type'] == 'deposit']['amount'].sum()
        total_withdrawals = deposits_df[deposits_df['type'] == 'withdraw']['amount'].sum()

    net_deposits = total_deposits - total_withdrawals

    # 순수익 = 최종자산 - 초기자산 - 순입금액
    gross_profit = final_asset - initial_asset
    net_profit = gross_profit - net_deposits

    # 순수익률 = 순수익 / (초기자산 + 순입금액)
    invested = initial_asset + net_deposits
    net_profit_rate = (net_profit / invested * 100) if invested > 0 else 0

    # 거래 통계
    total_trades = len(trades_df)
    buy_count = len(trades_df[trades_df['decision'] == 'buy'])
    sell_count = len(trades_df[trades_df['decision'] == 'sell'])
    hold_count = len(trades_df[trades_df['decision'] == 'hold'])

    return {
        'initial_asset': initial_asset,
        'final_asset': final_asset,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'net_deposits': net_deposits,
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'net_profit_rate': net_profit_rate,
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

    # 입출금 관리 섹션
    st.sidebar.markdown("---")
    st.sidebar.title("💵 입출금 관리")

    with st.sidebar.expander("➕ 입출금 기록 추가"):
        deposit_type = st.selectbox("유형", ["deposit", "withdraw"], format_func=lambda x: "입금" if x == "deposit" else "출금")
        amount = st.number_input("금액 (KRW)", min_value=0, step=10000)
        memo = st.text_input("메모 (선택)")

        if st.button("추가", type="primary"):
            if amount > 0:
                if add_deposit(amount, deposit_type, memo):
                    st.success("추가 완료!")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.warning("금액을 입력하세요")

    # 헤더
    st.title("📈 JWCoin Trading Dashboard")
    st.markdown("AI 자동매매 성과 모니터링")

    # 데이터 로드
    with st.spinner("데이터 로딩 중..."):
        trades_df = get_trades_from_supabase(days)
        deposits_df = get_deposits_from_supabase()
        current_price = get_current_btc_price()

    if trades_df.empty:
        st.warning("거래 기록이 없습니다.")
        st.stop()

    # 성과 계산
    perf = calculate_performance(trades_df, deposits_df)

    # 현재 상태
    st.header("💰 현재 상태")

    latest = trades_df.iloc[0]
    current_btc_value = latest['btc_balance'] * (current_price or latest['btc_krw_price'])
    current_total = latest['krw_balance'] + current_btc_value

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("보유 BTC", f"{latest['btc_balance']:.6f} BTC")
    with col2:
        st.metric("BTC 가치", f"{format_krw(current_btc_value)} KRW")
    with col3:
        st.metric("보유 KRW", f"{format_krw(latest['krw_balance'])} KRW")
    with col4:
        st.metric("총 자산", f"{format_krw(current_total)} KRW")

    # 성과 지표 (입금 제외)
    st.header("📊 투자 성과 (입출금 제외)")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "총 입금",
            f"{format_krw(perf.get('total_deposits', 0))} KRW"
        )
    with col2:
        st.metric(
            "총 출금",
            f"{format_krw(perf.get('total_withdrawals', 0))} KRW"
        )
    with col3:
        st.metric(
            "순 입금",
            f"{format_krw(perf.get('net_deposits', 0))} KRW"
        )
    with col4:
        net_profit = perf.get('net_profit', 0)
        st.metric(
            "순수익 (투자수익)",
            f"{format_krw(net_profit)} KRW",
            delta=f"{perf.get('net_profit_rate', 0):+.2f}%"
        )
    with col5:
        st.metric(
            "총 거래",
            f"{perf.get('total_trades', 0)}회",
            help=f"매수: {perf.get('buy_count', 0)} / 매도: {perf.get('sell_count', 0)} / 홀드: {perf.get('hold_count', 0)}"
        )

    # 차트
    st.header("📈 차트")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.plotly_chart(create_asset_chart(trades_df), use_container_width=True)
    with col2:
        st.plotly_chart(create_decision_chart(trades_df), use_container_width=True)

    st.plotly_chart(create_btc_chart(trades_df), use_container_width=True)

    # 탭으로 거래 기록과 입출금 기록 분리
    tab1, tab2 = st.tabs(["📜 거래 기록", "💵 입출금 기록"])

    with tab1:
        display_df = trades_df[['timestamp', 'decision', 'percentage', 'btc_balance', 'krw_balance', 'btc_krw_price', 'reason']].head(20).copy()
        display_df.columns = ['시간', '결정', '비율(%)', 'BTC 잔고', 'KRW 잔고', 'BTC 가격', '이유']
        display_df['시간'] = display_df['시간'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['결정'] = display_df['결정'].map({'buy': '🟢 매수', 'sell': '🔴 매도', 'hold': '⚪ 홀드'})
        display_df['BTC 잔고'] = display_df['BTC 잔고'].apply(lambda x: f"{x:.6f}")
        display_df['KRW 잔고'] = display_df['KRW 잔고'].apply(lambda x: f"{x:,.0f}")
        display_df['BTC 가격'] = display_df['BTC 가격'].apply(lambda x: f"{x:,.0f}")
        display_df['이유'] = display_df['이유'].apply(lambda x: x[:100] + '...' if len(str(x)) > 100 else x)

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # 거래 이유 번역 기능
        st.markdown("#### 🌐 거래 이유 번역")
        trade_idx = st.selectbox(
            "번역할 거래 선택",
            range(min(20, len(trades_df))),
            format_func=lambda i: f"{trades_df.iloc[i]['timestamp'].strftime('%Y-%m-%d %H:%M')} - {trades_df.iloc[i]['decision']}"
        )

        if st.button("🔤 한국어로 번역", key="translate_reason"):
            selected_reason = trades_df.iloc[trade_idx]['reason']
            with st.spinner("번역 중..."):
                translated = translate_to_korean(selected_reason)
            st.info(f"**원문:** {selected_reason}")
            st.success(f"**번역:** {translated}")

    with tab2:
        if not deposits_df.empty:
            dep_display = deposits_df.copy()
            dep_display['created_at'] = dep_display['created_at'].dt.strftime('%Y-%m-%d %H:%M')
            dep_display['type'] = dep_display['type'].map({'deposit': '🟢 입금', 'withdraw': '🔴 출금'})
            dep_display['amount'] = dep_display['amount'].apply(lambda x: f"{x:,.0f} KRW")
            dep_display = dep_display[['id', 'created_at', 'type', 'amount', 'memo']]
            dep_display.columns = ['ID', '시간', '유형', '금액', '메모']

            st.dataframe(dep_display, use_container_width=True, hide_index=True)

            # 삭제 기능
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            with col1:
                delete_id = st.number_input("삭제할 ID", min_value=1, step=1)
            with col2:
                if st.button("🗑️ 삭제", type="secondary"):
                    if delete_deposit(delete_id):
                        st.success("삭제 완료!")
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("입출금 기록이 없습니다. 사이드바에서 추가하세요.")

    # AI 분석
    if 'reflection' in trades_df.columns:
        st.header("🤖 AI 분석")
        latest_reflection = trades_df.iloc[0].get('reflection', '')
        if latest_reflection:
            st.markdown(f"**원문:**")
            st.markdown(f"> {latest_reflection}")

            if st.button("🔤 한국어로 번역", key="translate_reflection"):
                with st.spinner("번역 중..."):
                    translated_reflection = translate_to_korean(latest_reflection)
                st.markdown(f"**번역:**")
                st.success(translated_reflection)

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