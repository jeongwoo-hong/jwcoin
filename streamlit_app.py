import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ============================================================================
# 설정 및 상수
# ============================================================================

UPBIT_FEE_RATE = 0.0005  # 업비트 수수료율 0.05%

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def get_connection():
    """데이터베이스 연결"""
    return sqlite3.connect('bitcoin_trades.db')

def format_number(value):
    """숫자 포맷팅"""
    if pd.isna(value):
        return "0"
    
    try:
        num = float(value)
        if abs(num) >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif abs(num) >= 1_000:
            return f"{num/1_000:.0f}K"
        elif 0 < abs(num) < 1:
            return f"{num:.6f}"
        else:
            return f"{num:,.0f}"
    except:
        return str(value)

# ============================================================================
# 데이터 로드 및 처리
# ============================================================================

def load_data():
    """데이터베이스에서 거래 데이터 로드"""
    conn = get_connection()
    query = "SELECT * FROM trades ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) == 0:
        return df
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def detect_cash_flows(df):
    """입출금 감지"""
    df = df.copy().reset_index(drop=True)
    df['cash_flow_type'] = 'trade'
    df['deposit_amount'] = 0.0
    df['withdraw_amount'] = 0.0
    
    for i in range(1, len(df)):
        prev_btc = df.loc[i-1, 'btc_balance']
        curr_btc = df.loc[i, 'btc_balance']
        prev_krw = df.loc[i-1, 'krw_balance']
        curr_krw = df.loc[i, 'krw_balance']
        
        btc_change = abs(curr_btc - prev_btc)
        krw_change = curr_krw - prev_krw
        
        # BTC 변화 없고 KRW만 변화 = 입출금
        if btc_change < 0.000001 and abs(krw_change) > 100:
            if krw_change > 0:
                df.loc[i, 'cash_flow_type'] = 'deposit'
                df.loc[i, 'deposit_amount'] = krw_change
            else:
                df.loc[i, 'cash_flow_type'] = 'withdraw'
                df.loc[i, 'withdraw_amount'] = abs(krw_change)
    
    return df

def calculate_trading_amounts(df):
    """매수/매도 금액 계산"""
    df = df.copy()
    df['buy_amount'] = 0.0
    df['sell_amount'] = 0.0
    df['trading_fee'] = 0.0
    
    for i in range(len(df)):
        if df.loc[i, 'cash_flow_type'] != 'trade':
            continue
            
        if i == 0:
            if df.loc[i, 'btc_balance'] > 0:
                amount = df.loc[i, 'btc_balance'] * df.loc[i, 'btc_krw_price']
                df.loc[i, 'buy_amount'] = amount
                df.loc[i, 'trading_fee'] = amount * UPBIT_FEE_RATE
        else:
            prev_btc = df.loc[i-1, 'btc_balance']
            curr_btc = df.loc[i, 'btc_balance']
            btc_diff = curr_btc - prev_btc
            
            if btc_diff > 0.000001:  # 매수
                amount = btc_diff * df.loc[i, 'btc_krw_price']
                df.loc[i, 'buy_amount'] = amount
                df.loc[i, 'trading_fee'] = amount * UPBIT_FEE_RATE
            elif btc_diff < -0.000001:  # 매도
                amount = abs(btc_diff) * df.loc[i, 'btc_krw_price']
                df.loc[i, 'sell_amount'] = amount
                df.loc[i, 'trading_fee'] = amount * UPBIT_FEE_RATE
    
    return df

def calculate_performance(df):
    """투자 성과 계산"""
    df = df.copy()
    
    # 누적 계산
    df['cumulative_deposits'] = df['deposit_amount'].cumsum()
    df['cumulative_withdraws'] = df['withdraw_amount'].cumsum()
    df['cumulative_buy'] = df['buy_amount'].cumsum()
    df['cumulative_sell'] = df['sell_amount'].cumsum()
    df['cumulative_fees'] = df['trading_fee'].cumsum()
    
    for i in range(len(df)):
        # 현재 자산
        btc_value = df.loc[i, 'btc_balance'] * df.loc[i, 'btc_krw_price']
        krw_value = df.loc[i, 'krw_balance']
        total_asset = btc_value + krw_value
        
        # 실제 투자원금 = 입금 - 출금
        investment = df.loc[i, 'cumulative_deposits'] - df.loc[i, 'cumulative_withdraws']
        
        # 투자성과 = 현재자산 - 투자원금
        performance = total_asset - investment
        
        # 수익률
        if investment > 0:
            return_rate = (performance / investment) * 100
        else:
            return_rate = 0
        
        # 실현손익 (간단 계산)
        buy_total = df.loc[i, 'cumulative_buy']
        sell_total = df.loc[i, 'cumulative_sell']
        fees_total = df.loc[i, 'cumulative_fees']
        
        if sell_total > 0 and df.loc[i, 'btc_avg_buy_price'] > 0:
            sold_btc = sell_total / df.loc[i, 'btc_krw_price'] if df.loc[i, 'btc_krw_price'] > 0 else 0
            cost = sold_btc * df.loc[i, 'btc_avg_buy_price']
            realized_profit = sell_total - cost - (fees_total * 0.5)  # 매도 수수료 절반
        else:
            realized_profit = 0
        
        # 결과 저장
        df.loc[i, 'total_asset'] = total_asset
        df.loc[i, 'investment'] = investment
        df.loc[i, 'performance'] = performance
        df.loc[i, 'return_rate'] = return_rate
        df.loc[i, 'realized_profit'] = realized_profit
    
    return df

# ============================================================================
# 차트 생성
# ============================================================================

def create_performance_chart(df):
    """투자 성과 차트"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['total_asset'],
        mode='lines',
        name='현재 자산',
        line=dict(color='blue', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['investment'],
        mode='lines',
        name='투자원금',
        line=dict(color='orange', width=2, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['performance'],
        mode='lines',
        name='투자성과',
        line=dict(color='green', width=3),
        fill='tozeroy'
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)
    
    fig.update_layout(
        title='투자 성과 변화',
        xaxis_title='시간',
        yaxis_title='금액 (KRW)',
        height=400
    )
    
    return fig

def create_cashflow_chart(df):
    """입출금 차트"""
    fig = go.Figure()
    
    deposits = df[df['cash_flow_type'] == 'deposit']
    withdraws = df[df['cash_flow_type'] == 'withdraw']
    
    if len(deposits) > 0:
        fig.add_trace(go.Scatter(
            x=deposits['timestamp'],
            y=deposits['deposit_amount'],
            mode='markers',
            name='입금',
            marker=dict(color='blue', size=10, symbol='triangle-up')
        ))
    
    if len(withdraws) > 0:
        fig.add_trace(go.Scatter(
            x=withdraws['timestamp'],
            y=withdraws['withdraw_amount'] * -1,
            mode='markers',
            name='출금',
            marker=dict(color='red', size=10, symbol='triangle-down')
        ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['cumulative_deposits'] - df['cumulative_withdraws'],
        mode='lines',
        name='순입금액',
        line=dict(color='green', width=2)
    ))
    
    fig.update_layout(
        title='입출금 내역',
        xaxis_title='시간',
        yaxis_title='금액 (KRW)',
        height=400
    )
    
    return fig

# ============================================================================
# 메인 애플리케이션
# ============================================================================

def main():
    st.set_page_config(page_title="Bitcoin Dashboard", layout="wide")
    
    # 헤더
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title('🚀 Bitcoin Investment Dashboard')
    with col2:
        if st.button("🔄 새로고침", type="primary"):
            st.rerun()
    
    st.markdown("---")

    # 데이터 로드 및 처리
    df = load_data()
    
    if len(df) == 0:
        st.warning("거래 데이터가 없습니다.")
        return

    df = detect_cash_flows(df)
    df = calculate_trading_amounts(df)
    df = calculate_performance(df)
    
    latest = df.iloc[-1]
    
    # 입출금 현황
    deposits = len(df[df['cash_flow_type'] == 'deposit'])
    withdraws = len(df[df['cash_flow_type'] == 'withdraw'])
    
    if deposits > 0 or withdraws > 0:
        st.info(f"💰 입금 {deposits}회 ({latest['cumulative_deposits']:,.0f}원) | "
               f"출금 {withdraws}회 ({latest['cumulative_withdraws']:,.0f}원)")

    # 핵심 지표
    st.header('📊 투자 성과')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("투자원금", f"{format_number(latest['investment'])} KRW",
                 help="실제 투입한 돈 (입금 - 출금)")
    
    with col2:
        st.metric("현재 자산", f"{format_number(latest['total_asset'])} KRW",
                 help="BTC + KRW 총합")
    
    with col3:
        perf = latest['performance']
        status = "수익" if perf >= 0 else "손실"
        st.metric(f"투자{status}", f"{format_number(abs(perf))} KRW",
                 delta=f"{perf:+,.0f} KRW")
    
    with col4:
        rate = latest['return_rate']
        st.metric("수익률", f"{rate:.2f}%",
                 delta=f"{rate:+.2f}%")

    # 상세 정보
    st.markdown("---")
    st.header('📋 상세 정보')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("보유 BTC", f"{latest['btc_balance']:.6f} BTC")
    
    with col2:
        st.metric("보유 현금", f"{format_number(latest['krw_balance'])} KRW")
    
    with col3:
        st.metric("실현손익", f"{format_number(latest['realized_profit'])} KRW")
    
    with col4:
        st.metric("거래 수수료", f"{format_number(latest['cumulative_fees'])} KRW")

    # 차트
    st.markdown("---")
    st.header('📈 차트 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_perf = create_performance_chart(df)
        st.plotly_chart(fig_perf, use_container_width=True)
    
    with col2:
        fig_cash = create_cashflow_chart(df)
        st.plotly_chart(fig_cash, use_container_width=True)

    # 거래 내역
    st.markdown("---")
    st.header('📜 최근 내역')
    
    # 타입 번역
    type_map = {'trade': '거래', 'deposit': '입금', 'withdraw': '출금'}
    df_display = df[['timestamp', 'cash_flow_type', 'btc_krw_price', 'btc_balance', 'krw_balance']].copy()
    df_display['cash_flow_type'] = df_display['cash_flow_type'].map(type_map)
    df_display.columns = ['시간', '유형', 'BTC가격', 'BTC잔액', 'KRW잔액']
    
    st.dataframe(df_display.sort_values('시간', ascending=False).head(15), 
                use_container_width=True)

    # 최종 요약
    st.markdown("---")
    st.header('🎯 투자 요약')
    
    perf = latest['performance']
    
    if perf >= 0:
        st.success(f"""
        **🎉 현재 {perf:,.0f}원의 수익이 발생했습니다!**
        
        • 투자원금: {latest['investment']:,.0f}원  
        • 현재자산: {latest['total_asset']:,.0f}원  
        • 수익률: {latest['return_rate']:.2f}%  
        • 실현손익: {latest['realized_profit']:,.0f}원  
        """)
    else:
        st.error(f"""
        **📉 현재 {abs(perf):,.0f}원의 손실이 발생했습니다.**
        
        • 투자원금: {latest['investment']:,.0f}원  
        • 현재자산: {latest['total_asset']:,.0f}원  
        • 손실률: {latest['return_rate']:.2f}%  
        • 실현손익: {latest['realized_profit']:,.0f}원  
        """)

if __name__ == "__main__":
    main()