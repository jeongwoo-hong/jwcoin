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
    query = "SELECT * FROM trades ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) == 0:
        return df
    
    # 타임스탬프를 datetime으로 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 거래 이유 한국어 번역 (필요시)
    if 'reason' in df.columns:
        df['reason_kr'] = df['reason']
    
    # 누락된 컬럼들 초기화 (실제 데이터가 없는 경우 대비)
    if 'buy_amount' not in df.columns:
        df['buy_amount'] = 0.0
    if 'sell_amount' not in df.columns:
        df['sell_amount'] = 0.0
    if 'deposit_amount' not in df.columns:
        df['deposit_amount'] = 0.0
    if 'withdraw_amount' not in df.columns:
        df['withdraw_amount'] = 0.0
    
    return df

def calculate_portfolio_value(df):
    """포트폴리오 가치 계산"""
    df['btc_value'] = df['btc_balance'] * df['btc_krw_price']
    df['total_value'] = df['btc_value'] + df['krw_balance']
    return df

def calculate_accurate_buy_sell_amounts(df):
    """정확한 매수/매도 금액 계산 (BTC 잔액 변화 기준)"""
    df = df.copy()
    df['calculated_buy_amount'] = 0.0
    df['calculated_sell_amount'] = 0.0
    
    for i in range(len(df)):
        current_row = df.iloc[i]
        
        if i == 0:
            # 첫 거래
            if current_row['decision'] == 'buy':
                df.loc[i, 'calculated_buy_amount'] = current_row['btc_balance'] * current_row['btc_krw_price']
        else:
            prev_row = df.iloc[i-1]
            btc_diff = current_row['btc_balance'] - prev_row['btc_balance']
            
            if btc_diff > 0:  # BTC 증가 = 매수
                buy_amount = btc_diff * current_row['btc_krw_price']
                df.loc[i, 'calculated_buy_amount'] = buy_amount
            elif btc_diff < 0:  # BTC 감소 = 매도
                sell_amount = abs(btc_diff) * current_row['btc_krw_price']
                df.loc[i, 'calculated_sell_amount'] = sell_amount
    
    return df

def calculate_investment_performance(df):
    """업비트 방식의 정밀한 투자 성과 계산"""
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 정확한 매수/매도 금액 계산
    df = calculate_accurate_buy_sell_amounts(df)
    
    # 누적 계산을 위한 초기화
    cumulative_deposit = 0      # 누적 입금액
    cumulative_withdraw = 0     # 누적 출금액
    cumulative_buy = 0          # 누적 매수액
    cumulative_sell = 0         # 누적 매도액
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # 실제 데이터가 있으면 사용, 없으면 계산된 값 사용
        buy_amount = row['buy_amount'] if row['buy_amount'] > 0 else row['calculated_buy_amount']
        sell_amount = row['sell_amount'] if row['sell_amount'] > 0 else row['calculated_sell_amount']
        
        # 누적 계산
        cumulative_deposit += row['deposit_amount']
        cumulative_withdraw += row['withdraw_amount']
        cumulative_buy += buy_amount
        cumulative_sell += sell_amount
        
        # 투자원금 = 입금액 - 출금액 (실제 투입한 원화)
        principal = cumulative_deposit - cumulative_withdraw
        
        # 현재 자산 가치
        current_btc_value = row['btc_balance'] * row['btc_krw_price']
        current_krw = row['krw_balance']
        total_asset_value = current_btc_value + current_krw
        
        # 실현손익 계산 (매도를 통해 확정된 손익)
        if cumulative_buy > 0:
            # 평균 매수가 계산
            total_btc_bought = cumulative_buy / (cumulative_buy / max(cumulative_buy / row['btc_krw_price'], 0.000001))
            avg_buy_price = cumulative_buy / max(total_btc_bought, 0.000001) if total_btc_bought > 0 else 0
            
            # 매도한 BTC의 원가
            btc_sold_total = cumulative_sell / row['btc_krw_price'] if row['btc_krw_price'] > 0 else 0
            cost_of_sold_btc = btc_sold_total * avg_buy_price
            realized_profit = cumulative_sell - cost_of_sold_btc
        else:
            realized_profit = 0
        
        # 평가손익 (현재 보유 BTC의 미실현 손익)
        if cumulative_buy > 0 and row['btc_balance'] > 0:
            remaining_btc_cost = (cumulative_buy - cumulative_sell) * (row['btc_balance'] / max(cumulative_buy - cumulative_sell, 0.000001))
            unrealized_profit = current_btc_value - remaining_btc_cost
        else:
            unrealized_profit = current_btc_value  # 전체가 수익
        
        # 총 손익
        total_profit = realized_profit + unrealized_profit
        
        # 수익률 계산 (투자원금 기준)
        if principal > 0:
            return_rate = (total_profit / principal) * 100
        else:
            return_rate = 0
        
        # 결과 저장
        df.loc[i, 'principal'] = principal
        df.loc[i, 'cumulative_deposit'] = cumulative_deposit
        df.loc[i, 'cumulative_withdraw'] = cumulative_withdraw
        df.loc[i, 'cumulative_buy'] = cumulative_buy
        df.loc[i, 'cumulative_sell'] = cumulative_sell
        df.loc[i, 'realized_profit'] = realized_profit
        df.loc[i, 'unrealized_profit'] = unrealized_profit
        df.loc[i, 'total_profit'] = total_profit
        df.loc[i, 'return_rate'] = return_rate
        df.loc[i, 'asset_value'] = total_asset_value
    
    # 일별 수익률
    df['daily_return'] = df['asset_value'].pct_change() * 100
    
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
        color = "normal" if total_return >= 0 else "inverse"
        st.metric("총 수익률", f"{formatted_return}%", 
                 delta=f"{total_return:.2f}%" if total_return != 0 else None)
    
    with col3:
        total_profit = latest_trade['total_profit']
        formatted_profit = format_metric_text(f"{total_profit:,.0f}")
        color = "normal" if total_profit >= 0 else "inverse"
        st.metric("총 손익", f"{formatted_profit} KRW",
                 delta=f"{total_profit:,.0f} KRW" if total_profit != 0 else None)
    
    with col4:
        principal = latest_trade['principal']
        formatted_principal = format_metric_text(f"{principal:,.0f}")
        st.metric("투자원금", f"{formatted_principal} KRW")
    
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

    # 6. 거래 통계 추가
    st.header('📊 거래 통계')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_trades = len(df)
        st.metric("총 거래횟수", f"{total_trades}회")
    
    with col2:
        buy_trades = len(df[df['decision'] == 'buy'])
        st.metric("매수 거래", f"{buy_trades}회")
    
    with col3:
        sell_trades = len(df[df['decision'] == 'sell'])
        st.metric("매도 거래", f"{sell_trades}회")
    
    with col4:
        if buy_trades > 0:
            avg_buy_amount = latest_trade['cumulative_buy'] / buy_trades
            st.metric("평균 매수금액", f"{format_metric_text(avg_buy_amount)} KRW")
        else:
            st.metric("평균 매수금액", "0 KRW")

    # 7. 수익률 분석
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

    # 8. 상세 투자 성과
    st.header('💹 상세 투자 성과')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("💰 투자원금 현황")
        total_deposit = latest_trade['cumulative_deposit']
        total_withdraw = latest_trade['cumulative_withdraw']
        principal = latest_trade['principal']
        
        st.metric("총 입금액", f"{format_metric_text(total_deposit)} KRW")
        st.metric("총 출금액", f"{format_metric_text(total_withdraw)} KRW") 
        st.metric("투자원금", f"{format_metric_text(principal)} KRW")
    
    with col2:
        st.subheader("📈 매수/매도 현황")
        total_buy = latest_trade['cumulative_buy']
        total_sell = latest_trade['cumulative_sell']
        
        st.metric("총 매수금액", f"{format_metric_text(total_buy)} KRW")
        st.metric("총 매도금액", f"{format_metric_text(total_sell)} KRW")
        net_trading = total_buy - total_sell
        st.metric("순거래금액", f"{format_metric_text(net_trading)} KRW")
    
    with col3:
        st.subheader("💰 손익 분석")
        realized = latest_trade['realized_profit']
        unrealized = latest_trade['unrealized_profit']
        total = latest_trade['total_profit']
        
        st.metric("실현손익", f"{format_metric_text(realized)} KRW",
                 delta="실현됨" if realized != 0 else None)
        st.metric("평가손익", f"{format_metric_text(unrealized)} KRW",
                 delta="미실현" if unrealized != 0 else None)
        st.metric("총 손익", f"{format_metric_text(total)} KRW")

    # 9. 거래 패턴 분석
    st.header('🎯 거래 패턴 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_decision = create_decision_pie_chart(df)
        st.plotly_chart(fig_decision, use_container_width=True)
    
    with col2:
        fig_monthly = create_monthly_trades_chart(df)
        st.plotly_chart(fig_monthly, use_container_width=True)

    # 10. BTC 가격 & 거래 포인트
    st.header('📈 BTC 가격 & 거래 포인트')
    fig_combined = create_price_and_trades_chart(df)
    st.plotly_chart(fig_combined, use_container_width=True)

    # 11. 자산 구성 변화
    st.header('💎 자산 구성 변화')
    fig_composition = create_asset_composition_chart(df)
    st.plotly_chart(fig_composition, use_container_width=True)

    # 12. 거래 내역 (최신순)
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

    # 13. 실시간 성과 요약
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
        **투자원금**: {latest_trade['principal']:,.0f} KRW  
        """)
    
    if 'reason_kr' in df.columns and pd.notna(latest_trade['reason_kr']):
        st.write(f"**거래 이유**: {latest_trade['reason_kr']}")
    elif 'reason' in df.columns and pd.notna(latest_trade['reason']):
        st.write(f"**거래 이유**: {latest_trade['reason']}")

if __name__ == "__main__":
    main()