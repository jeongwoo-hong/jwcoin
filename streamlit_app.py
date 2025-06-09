import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def get_connection():
    """데이터베이스 연결"""
    return sqlite3.connect('bitcoin_trades.db')

def format_metric_text(value, max_length=12):
    """메트릭 텍스트의 길이를 자동으로 조절"""
    text = str(value)
    if len(text) <= max_length:
        return text
    
    try:
        num = float(value)
        if abs(num) >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif abs(num) >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif abs(num) >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:.1f}"
    except:
        return text[:max_length-3] + "..." if len(text) > max_length else text

# ============================================================================
# 데이터 처리 함수들
# ============================================================================

def load_data():
    """데이터베이스에서 거래 데이터 로드"""
    conn = get_connection()
    query = "SELECT * FROM trades ORDER BY timestamp ASC"  # 시간순으로 로드
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) == 0:
        return df
    
    # 타임스탬프를 datetime으로 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 거래 이유 한국어 번역 (필요시)
    if 'reason' in df.columns:
        df['reason_kr'] = df['reason']  # 실제 번역 로직은 필요시 추가
    
    return df

def calculate_portfolio_value(df):
    """포트폴리오 가치 계산"""
    df['total_value'] = df['btc_balance'] * df['btc_krw_price'] + df['krw_balance']
    return df

def calculate_investment_performance(df):
    """정밀한 투자 성과 계산 (매도금액 반영)"""
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 초기화
    total_buy_amount = 0
    total_sell_amount = 0
    
    for i in range(len(df)):
        trade = df.iloc[i]
        
        if trade['decision'] == 'buy':
            # 매수량 계산
            if i > 0:
                prev_btc = df.iloc[i-1]['btc_balance']
                btc_bought = trade['btc_balance'] - prev_btc
            else:
                btc_bought = trade['btc_balance']
            
            buy_amount = btc_bought * trade['btc_krw_price']
            total_buy_amount += max(0, buy_amount)
            
        elif trade['decision'] == 'sell':
            # 매도량 계산
            if i > 0:
                prev_btc = df.iloc[i-1]['btc_balance']
                btc_sold = prev_btc - trade['btc_balance']
            else:
                btc_sold = 0
            
            sell_amount = btc_sold * trade['btc_krw_price']
            total_sell_amount += max(0, sell_amount)
        
        # 각 시점의 성과 계산
        net_investment = total_buy_amount - total_sell_amount
        current_btc_value = trade['btc_balance'] * trade['btc_krw_price']
        
        # 평가손익 = 현재 BTC 가치 + KRW 잔액 - 순투자금액
        unrealized_profit = current_btc_value + trade['krw_balance'] - net_investment
        
        # 실현손익 = 총 매도금액 - 매도한 BTC의 평균 매수가
        if total_buy_amount > 0 and total_sell_amount > 0:
            avg_buy_price_per_btc = total_buy_amount / max(trade['btc_balance'] + (total_sell_amount / trade['btc_krw_price']), 0.000001)
            realized_profit = total_sell_amount - (total_sell_amount / trade['btc_krw_price']) * avg_buy_price_per_btc
        else:
            realized_profit = 0
        
        total_profit = realized_profit + unrealized_profit
        
        # 수익률 계산
        return_rate = (total_profit / net_investment * 100) if net_investment > 0 else 0
        
        # 결과 저장
        df.loc[i, 'total_buy_amount'] = total_buy_amount
        df.loc[i, 'total_sell_amount'] = total_sell_amount
        df.loc[i, 'net_investment'] = net_investment
        df.loc[i, 'realized_profit'] = realized_profit
        df.loc[i, 'unrealized_profit'] = unrealized_profit
        df.loc[i, 'total_profit'] = total_profit
        df.loc[i, 'return_rate'] = return_rate
    
    # 일별 수익률
    df['daily_return'] = df['total_value'].pct_change() * 100
    
    return df

# ============================================================================
# 차트 생성 함수들
# ============================================================================

def create_portfolio_chart(df):
    """포트폴리오 가치 변화 차트"""
    fig = px.line(df, x='timestamp', y='total_value',
                  title='포트폴리오 총 가치 변화',
                  labels={'total_value': '포트폴리오 가치 (KRW)', 'timestamp': '시간'})
    fig.update_traces(line=dict(width=3, color='#1f77b4'))
    fig.update_layout(height=400)
    return fig

def create_return_chart(df):
    """수익률 변화 차트"""
    fig = px.line(df, x='timestamp', y='return_rate',
                  title='총 수익률 변화 (%)',
                  labels={'return_rate': '수익률 (%)', 'timestamp': '시간'})
    fig.update_traces(line=dict(width=2, color='#2ca02c'))
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7)
    return fig

def create_daily_return_histogram(df):
    """일별 수익률 분포 히스토그램"""
    daily_returns = df['daily_return'].dropna()
    if len(daily_returns) <= 1:
        return None
    
    fig = px.histogram(x=daily_returns, nbins=20,
                      title='일별 수익률 분포',
                      labels={'x': '일별 수익률 (%)', 'count': '빈도'})
    fig.add_vline(x=daily_returns.mean(), line_dash="dash", 
                  line_color="red", annotation_text=f"평균: {daily_returns.mean():.2f}%")
    return fig

def create_decision_pie_chart(df):
    """거래 결정 분포 파이 차트"""
    decision_counts = df['decision'].value_counts()
    fig = px.pie(values=decision_counts.values, names=decision_counts.index, 
                 title='거래 결정 분포', hole=0.4)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_monthly_trades_chart(df):
    """월별 거래 횟수 차트"""
    df['month'] = df['timestamp'].dt.to_period('M').astype(str)
    monthly_trades = df.groupby('month').size().reset_index(name='trades')
    fig = px.bar(monthly_trades, x='month', y='trades',
                title='월별 거래 횟수',
                labels={'month': '월', 'trades': '거래 횟수'})
    fig.update_traces(marker_color='lightblue')
    return fig

def create_price_and_trades_chart(df):
    """BTC 가격 & 거래 포인트 차트"""
    fig = go.Figure()
    
    # BTC 가격 라인
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['btc_krw_price'],
        mode='lines',
        name='BTC 가격',
        line=dict(color='orange', width=2)
    ))
    
    # 매수 포인트
    buy_trades = df[df['decision'] == 'buy']
    if len(buy_trades) > 0:
        fig.add_trace(go.Scatter(
            x=buy_trades['timestamp'],
            y=buy_trades['btc_krw_price'],
            mode='markers',
            name='매수',
            marker=dict(color='green', size=10, symbol='triangle-up')
        ))
    
    # 매도 포인트
    sell_trades = df[df['decision'] == 'sell']
    if len(sell_trades) > 0:
        fig.add_trace(go.Scatter(
            x=sell_trades['timestamp'],
            y=sell_trades['btc_krw_price'],
            mode='markers',
            name='매도',
            marker=dict(color='red', size=10, symbol='triangle-down')
        ))
    
    fig.update_layout(
        title='BTC 가격 변화 및 거래 포인트',
        xaxis_title='시간',
        yaxis_title='BTC 가격 (KRW)',
        height=500
    )
    
    return fig

def create_asset_composition_chart(df):
    """자산 구성 비율 변화 차트"""
    df['btc_value'] = df['btc_balance'] * df['btc_krw_price']
    df['btc_ratio'] = (df['btc_value'] / df['total_value']) * 100
    df['krw_ratio'] = (df['krw_balance'] / df['total_value']) * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['btc_ratio'],
        fill='tonexty',
        mode='lines',
        name='BTC 비율 (%)',
        line=dict(color='orange')
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['krw_ratio'],
        fill='tozeroy',
        mode='lines',
        name='KRW 비율 (%)',
        line=dict(color='blue')
    ))
    
    fig.update_layout(
        title='자산 구성 비율 변화',
        xaxis_title='시간',
        yaxis_title='비율 (%)',
        yaxis=dict(range=[0, 100]),
        height=400
    )
    
    return fig

# ============================================================================
# 메인 애플리케이션
# ============================================================================

def main():
    st.set_page_config(page_title="Bitcoin Trading Dashboard", layout="wide")
    st.title('🚀 Bitcoin Trading Dashboard')
    st.markdown("---")

    # 1. 데이터 로드 및 처리
    df = load_data()
    
    if len(df) == 0:
        st.warning("거래 데이터가 없습니다.")
        return

    # 데이터 처리
    df = calculate_portfolio_value(df)
    df = calculate_investment_performance(df)
    
    latest_trade = df.iloc[-1]  # 최신 거래
    
    # 2. 핵심 지표 (KPI)
    st.header('📈 핵심 투자 지표')
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        current_value = latest_trade['total_value']
        formatted_value = format_metric_text(f"{current_value:,.0f}")
        st.metric("포트폴리오 가치", f"{formatted_value} KRW")
    
    with col2:
        total_return = latest_trade['return_rate']
        formatted_return = format_metric_text(f"{total_return:.2f}")
        st.metric("총 수익률", f"{formatted_return}%", 
                 delta=f"{total_return:.2f}%" if total_return != 0 else None)
    
    with col3:
        total_profit = latest_trade['total_profit']
        formatted_profit = format_metric_text(f"{total_profit:,.0f}")
        color = "normal" if total_profit >= 0 else "inverse"
        st.metric("총 손익", f"{formatted_profit} KRW",
                 delta=f"{total_profit:,.0f} KRW" if total_profit != 0 else None)
    
    with col4:
        net_investment = latest_trade['net_investment']
        formatted_investment = format_metric_text(f"{net_investment:,.0f}")
        st.metric("순투자금액", f"{formatted_investment} KRW")
    
    with col5:
        current_btc = latest_trade['btc_balance']
        formatted_btc = format_metric_text(f"{current_btc:.6f}")
        st.metric("보유 BTC", f"{formatted_btc} BTC")

    st.markdown("---")

    # 3. 기본 통계
    st.header('📋 거래 기간 정보')
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**첫 거래일**: {df['timestamp'].min().strftime('%Y-%m-%d %H:%M')}")
    with col2:
        st.write(f"**최근 거래일**: {df['timestamp'].max().strftime('%Y-%m-%d %H:%M')}")
    with col3:
        trading_days = (df['timestamp'].max() - df['timestamp'].min()).days
        st.write(f"**거래 기간**: {trading_days}일")

    # 4. 포트폴리오 가치 차트
    st.header('💰 포트폴리오 가치 변화')
    fig_portfolio = create_portfolio_chart(df)
    st.plotly_chart(fig_portfolio, use_container_width=True)

    # 5. 수익률 분석
    st.header('📊 수익률 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_return = create_return_chart(df)
        st.plotly_chart(fig_return, use_container_width=True)
    
    with col2:
        fig_hist = create_daily_return_histogram(df)
        if fig_hist:
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("일별 수익률 데이터가 부족합니다.")

    # 6. 상세 투자 성과
    st.header('💹 상세 투자 성과')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📈 매수/매도 현황")
        total_buy = latest_trade['total_buy_amount']
        total_sell = latest_trade['total_sell_amount']
        
        st.metric("총 매수금액", f"{format_metric_text(total_buy)} KRW")
        st.metric("총 매도금액", f"{format_metric_text(total_sell)} KRW")
        st.metric("순투자금액", f"{format_metric_text(total_buy - total_sell)} KRW")
    
    with col2:
        st.subheader("💰 손익 분석")
        realized = latest_trade['realized_profit']
        unrealized = latest_trade['unrealized_profit']
        total = latest_trade['total_profit']
        
        st.metric("실현손익", f"{format_metric_text(realized)} KRW",
                 delta="실현됨" if realized != 0 else None)
        st.metric("평가손익", f"{format_metric_text(unrealized)} KRW",
                 delta="미실현" if unrealized != 0 else None)
        st.metric("총 손익", f"{format_metric_text(total)} KRW")
    
    with col3:
        st.subheader("📊 거래 통계")
        total_trades = len(df)
        buy_trades = len(df[df['decision'] == 'buy'])
        sell_trades = len(df[df['decision'] == 'sell'])
        
        st.metric("총 거래횟수", f"{total_trades}회")
        st.metric("매수 거래", f"{buy_trades}회")
        st.metric("매도 거래", f"{sell_trades}회")

    # 7. 거래 패턴 분석
    st.header('🎯 거래 패턴 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_decision = create_decision_pie_chart(df)
        st.plotly_chart(fig_decision, use_container_width=True)
    
    with col2:
        fig_monthly = create_monthly_trades_chart(df)
        st.plotly_chart(fig_monthly, use_container_width=True)

    # 8. BTC 가격 & 거래 포인트
    st.header('📈 BTC 가격 & 거래 포인트')
    fig_combined = create_price_and_trades_chart(df)
    st.plotly_chart(fig_combined, use_container_width=True)

    # 9. 자산 구성 변화
    st.header('💎 자산 구성 변화')
    fig_composition = create_asset_composition_chart(df)
    st.plotly_chart(fig_composition, use_container_width=True)

    # 10. 거래 내역 (최신순)
    st.header('📜 거래 내역 (최신순)')
    display_columns = ['timestamp', 'decision', 'btc_krw_price', 'btc_balance', 'krw_balance']
    
    available_columns = [col for col in display_columns if col in df.columns]
    if 'reason_kr' in df.columns:
        available_columns.append('reason_kr')
    elif 'reason' in df.columns:
        available_columns.append('reason')
    
    # 최신순으로 정렬하여 표시
    df_display = df.sort_values('timestamp', ascending=False)
    styled_df = df_display[available_columns].head(20)
    st.dataframe(styled_df, use_container_width=True)

    # 11. 실시간 성과 요약
    st.header('🎯 실시간 성과 요약')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **최근 거래 결정**: {latest_trade['decision']}  
        **거래 시간**: {latest_trade['timestamp']}  
        **BTC 가격**: {latest_trade['btc_krw_price']:,.0f} KRW  
        **수익률**: {latest_trade['return_rate']:.2f}%  
        """)
    
    with col2:
        st.success(f"""
        **현재 BTC 잔액**: {latest_trade['btc_balance']:.6f} BTC  
        **현재 KRW 잔액**: {latest_trade['krw_balance']:,.0f} KRW  
        **포트폴리오 가치**: {latest_trade['total_value']:,.0f} KRW  
        **총 손익**: {latest_trade['total_profit']:,.0f} KRW  
        """)
    
    if 'reason_kr' in df.columns and pd.notna(latest_trade['reason_kr']):
        st.write(f"**거래 이유**: {latest_trade['reason_kr']}")
    elif 'reason' in df.columns and pd.notna(latest_trade['reason']):
        st.write(f"**거래 이유**: {latest_trade['reason']}")

if __name__ == "__main__":
    main()