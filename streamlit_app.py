import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# 데이터베이스 연결 함수
def get_connection():
    return sqlite3.connect('bitcoin_trades.db')

# 데이터 로드 함수
def load_data():
    conn = get_connection()
    query = "SELECT * FROM trades ORDER BY timestamp DESC"  # 최신순으로 정렬
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # 거래 이유를 한국어로 번역
    if 'reason' in df.columns:
        df['reason_kr'] = df['reason']
    
    # 타임스탬프를 datetime으로 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

# 포트폴리오 가치 계산 함수
def calculate_portfolio_value(df):
    df_sorted = df.sort_values('timestamp')
    df_sorted['total_value'] = df_sorted['btc_balance'] * df_sorted['btc_krw_price'] + df_sorted['krw_balance']
    return df_sorted

# 수익률 계산 함수 (매수 금액 기준)
def calculate_returns(df):
    df_sorted = df.sort_values('timestamp')
    
    # 매수 거래만 필터링하여 총 투자 금액 계산
    buy_trades = df_sorted[df_sorted['decision'] == 'buy'].copy()
    
    if len(buy_trades) > 0:
        # 각 매수 거래의 투자 금액 계산 (이전 잔액에서 현재 잔액을 뺀 값)
        total_invested = 0
        
        for i, trade in buy_trades.iterrows():
            # 매수한 BTC 수량을 추정 (이전 거래와 비교)
            prev_trades = df_sorted[df_sorted['timestamp'] < trade['timestamp']]
            if len(prev_trades) > 0:
                prev_btc = prev_trades.iloc[-1]['btc_balance']
                btc_bought = trade['btc_balance'] - prev_btc
                invested_amount = btc_bought * trade['btc_krw_price']
                total_invested += invested_amount
            else:
                # 첫 거래인 경우
                invested_amount = trade['btc_balance'] * trade['btc_krw_price']
                total_invested += invested_amount
        
        # 매수 금액 대비 수익률 계산
        if total_invested > 0:
            df_sorted['invested_amount'] = total_invested
            df_sorted['investment_return'] = ((df_sorted['total_value'] - total_invested) / total_invested) * 100
        else:
            df_sorted['invested_amount'] = 0
            df_sorted['investment_return'] = 0
    else:
        df_sorted['invested_amount'] = 0
        df_sorted['investment_return'] = 0
    
    # 일별 수익률 (전날 대비)
    df_sorted['daily_return'] = df_sorted['total_value'].pct_change() * 100
    
    return df_sorted

# 메인 함수
def main():
    st.title('🚀 Bitcoin Trading Dashboard')
    st.markdown("---")

    # 데이터 로드
    df = load_data()
    
    if len(df) == 0:
        st.warning("거래 데이터가 없습니다.")
        return

    # 포트폴리오 가치 및 수익률 계산
    df_with_portfolio = calculate_portfolio_value(df)
    df_with_returns = calculate_returns(df_with_portfolio)
    
    # 계산된 데이터프레임을 사용
    df = df_with_returns

    # 📊 핵심 지표 (KPI)
    st.header('📈 핵심 투자 지표')
    
    col1, col2, col3, col4 = st.columns(4)
    
    latest_trade = df_with_returns.iloc[-1] if len(df_with_returns) > 0 else None
    first_trade = df_with_returns.iloc[0] if len(df_with_returns) > 0 else None
    
    with col1:
        current_value = latest_trade['total_value'] if latest_trade is not None else 0
        st.metric("현재 포트폴리오 가치", f"{current_value:,.0f} KRW")
    
    with col2:
        total_return = latest_trade['investment_return'] if latest_trade is not None else 0
        invested_amount = latest_trade['invested_amount'] if latest_trade is not None else 0
        st.metric("매수 대비 수익률", f"{total_return:.2f}%", 
                 delta=f"{total_return:.2f}%" if total_return != 0 else None)
        if invested_amount > 0:
            st.caption(f"총 투자금액: {invested_amount:,.0f} KRW")
    
    with col3:
        total_trades = len(df)
        buy_trades = len(df[df['decision'] == 'buy'])
        st.metric("총 거래 횟수", f"{total_trades}회", 
                 delta=f"매수: {buy_trades}회")
    
    with col4:
        current_btc = latest_trade['btc_balance'] if latest_trade is not None else 0
        st.metric("보유 BTC", f"{current_btc:.6f} BTC")

    st.markdown("---")

    # 기본 통계 (간소화)
    st.header('📋 Basic Statistics')
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**첫 거래일**: {df['timestamp'].min().strftime('%Y-%m-%d')}")
    with col2:
        st.write(f"**최근 거래일**: {df['timestamp'].max().strftime('%Y-%m-%d')}")
    with col3:
        trading_days = (df['timestamp'].max() - df['timestamp'].min()).days
        st.write(f"**거래 기간**: {trading_days}일")

    # 🔥 포트폴리오 가치 변화 (메인 차트)
    st.header('💰 포트폴리오 가치 변화')
    fig_portfolio = px.line(df.sort_values('timestamp'), 
                           x='timestamp', y='total_value',
                           title='포트폴리오 총 가치 변화',
                           labels={'total_value': '포트폴리오 가치 (KRW)', 'timestamp': '시간'})
    fig_portfolio.update_traces(line=dict(width=3, color='#1f77b4'))
    fig_portfolio.update_layout(height=400)
    st.plotly_chart(fig_portfolio, use_container_width=True)

    # 📊 수익률 차트
    st.header('📊 수익률 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 누적 수익률 (매수 금액 기준)
        fig_return = px.line(df.sort_values('timestamp'), 
                            x='timestamp', y='investment_return',
                            title='매수 대비 누적 수익률 (%)',
                            labels={'investment_return': '수익률 (%)', 'timestamp': '시간'})
        fig_return.update_traces(line=dict(width=2, color='#2ca02c'))
        fig_return.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7)
        st.plotly_chart(fig_return, use_container_width=True)
    
    with col2:
        # 일별 수익률 히스토그램
        daily_returns = df['daily_return'].dropna()
        if len(daily_returns) > 1:
            fig_hist = px.histogram(x=daily_returns, nbins=20,
                                  title='일별 수익률 분포',
                                  labels={'x': '일별 수익률 (%)', 'count': '빈도'})
            fig_hist.add_vline(x=daily_returns.mean(), line_dash="dash", 
                              line_color="red", annotation_text=f"평균: {daily_returns.mean():.2f}%")
            st.plotly_chart(fig_hist, use_container_width=True)

    # 🎯 거래 패턴 분석
    st.header('🎯 거래 패턴 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 거래 결정 분포 (도넛 차트)
        decision_counts = df['decision'].value_counts()
        fig_decision = px.pie(values=decision_counts.values, names=decision_counts.index, 
                             title='거래 결정 분포', hole=0.4)
        fig_decision.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_decision, use_container_width=True)
    
    with col2:
        # 월별 거래 횟수
        df['month'] = df['timestamp'].dt.to_period('M').astype(str)
        monthly_trades = df.groupby('month').size().reset_index(name='trades')
        fig_monthly = px.bar(monthly_trades, x='month', y='trades',
                            title='월별 거래 횟수',
                            labels={'month': '월', 'trades': '거래 횟수'})
        fig_monthly.update_traces(marker_color='lightblue')
        st.plotly_chart(fig_monthly, use_container_width=True)

    # 📈 통합 차트 (BTC 가격 + 거래 포인트)
    st.header('📈 BTC 가격 & 거래 포인트')
    
    df_chart = df.sort_values('timestamp')
    
    fig_combined = go.Figure()
    
    # BTC 가격 라인
    fig_combined.add_trace(go.Scatter(
        x=df_chart['timestamp'], 
        y=df_chart['btc_krw_price'],
        mode='lines',
        name='BTC 가격',
        line=dict(color='orange', width=2)
    ))
    
    # 매수 포인트
    buy_trades = df_chart[df_chart['decision'] == 'buy']
    if len(buy_trades) > 0:
        fig_combined.add_trace(go.Scatter(
            x=buy_trades['timestamp'],
            y=buy_trades['btc_krw_price'],
            mode='markers',
            name='매수',
            marker=dict(color='green', size=10, symbol='triangle-up')
        ))
    
    # 매도 포인트
    sell_trades = df_chart[df_chart['decision'] == 'sell']
    if len(sell_trades) > 0:
        fig_combined.add_trace(go.Scatter(
            x=sell_trades['timestamp'],
            y=sell_trades['btc_krw_price'],
            mode='markers',
            name='매도',
            marker=dict(color='red', size=10, symbol='triangle-down')
        ))
    
    fig_combined.update_layout(
        title='BTC 가격 변화 및 거래 포인트',
        xaxis_title='시간',
        yaxis_title='BTC 가격 (KRW)',
        height=500
    )
    
    st.plotly_chart(fig_combined, use_container_width=True)

    # 💎 자산 구성 변화
    st.header('💎 자산 구성 변화')
    
    # BTC vs KRW 비율 차트
    df_sorted = df.sort_values('timestamp')
    
    # 이미 계산된 total_value를 사용
    df_sorted['btc_value'] = df_sorted['btc_balance'] * df_sorted['btc_krw_price']
    df_sorted['btc_ratio'] = (df_sorted['btc_value'] / df_sorted['total_value']) * 100
    df_sorted['krw_ratio'] = (df_sorted['krw_balance'] / df_sorted['total_value']) * 100
    
    fig_composition = go.Figure()
    
    fig_composition.add_trace(go.Scatter(
        x=df_sorted['timestamp'], 
        y=df_sorted['btc_ratio'],
        fill='tonexty',
        mode='lines',
        name='BTC 비율 (%)',
        line=dict(color='orange')
    ))
    
    fig_composition.add_trace(go.Scatter(
        x=df_sorted['timestamp'], 
        y=df_sorted['krw_ratio'],
        fill='tozeroy',
        mode='lines',
        name='KRW 비율 (%)',
        line=dict(color='blue')
    ))
    
    fig_composition.update_layout(
        title='자산 구성 비율 변화',
        xaxis_title='시간',
        yaxis_title='비율 (%)',
        yaxis=dict(range=[0, 100]),
        height=400
    )
    
    st.plotly_chart(fig_composition, use_container_width=True)

    # 거래 내역 표시
    st.header('📜 거래 내역 (최신순)')
    display_columns = ['timestamp', 'decision', 'btc_krw_price', 'btc_balance', 'krw_balance']
    
    available_columns = [col for col in display_columns if col in df.columns]
    if 'reason_kr' in df.columns:
        available_columns.append('reason_kr')
    elif 'reason' in df.columns:
        available_columns.append('reason')
    
    # 데이터프레임 스타일링
    styled_df = df[available_columns].head(20)  # 최근 20개만 표시
    st.dataframe(styled_df, use_container_width=True)

    # 최근 거래 요약
    st.header('🎯 최근 거래 요약')
    if len(df) > 0:
        latest_trade = df.iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **최근 거래 결정**: {latest_trade['decision']}  
            **거래 시간**: {latest_trade['timestamp']}  
            **BTC 가격**: {latest_trade['btc_krw_price']:,.0f} KRW  
            """)
        
        with col2:
            st.success(f"""
            **현재 BTC 잔액**: {latest_trade['btc_balance']:.6f} BTC  
            **현재 KRW 잔액**: {latest_trade['krw_balance']:,.0f} KRW  
            **포트폴리오 가치**: {current_value:,.0f} KRW  
            """)
        
        if 'reason_kr' in df.columns and pd.notna(latest_trade['reason_kr']):
            st.write(f"**거래 이유**: {latest_trade['reason_kr']}")
        elif 'reason' in df.columns and pd.notna(latest_trade['reason']):
            st.write(f"**거래 이유**: {latest_trade['reason']}")

if __name__ == "__main__":
    main()