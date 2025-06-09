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
    
    # 거래 이유 한국어 번역
    if 'reason' in df.columns:
        df['reason_kr'] = df['reason']
    
    return df

def calculate_portfolio_value(df):
    """포트폴리오 가치 계산"""
    df['btc_value'] = df['btc_balance'] * df['btc_krw_price']
    df['total_value'] = df['btc_value'] + df['krw_balance']
    return df

def calculate_accurate_trades(df):
    """BTC 잔액 변화를 통한 정확한 매수/매도 금액 계산"""
    df = df.copy()
    df['buy_amount'] = 0.0
    df['sell_amount'] = 0.0
    df['btc_traded'] = 0.0
    
    for i in range(len(df)):
        current_row = df.iloc[i]
        
        if i == 0:
            # 첫 거래 - 전체 BTC를 매수한 것으로 가정
            if current_row['btc_balance'] > 0:
                df.loc[i, 'buy_amount'] = current_row['btc_balance'] * current_row['btc_krw_price']
                df.loc[i, 'btc_traded'] = current_row['btc_balance']
        else:
            prev_row = df.iloc[i-1]
            btc_diff = current_row['btc_balance'] - prev_row['btc_balance']
            
            if btc_diff > 0:  # BTC 증가 = 매수
                df.loc[i, 'buy_amount'] = btc_diff * current_row['btc_krw_price']
                df.loc[i, 'btc_traded'] = btc_diff
            elif btc_diff < 0:  # BTC 감소 = 매도
                df.loc[i, 'sell_amount'] = abs(btc_diff) * current_row['btc_krw_price']
                df.loc[i, 'btc_traded'] = btc_diff
    
    return df

def calculate_investment_performance(df):
    """정확한 투자 성과 계산 (btc_avg_buy_price 활용)"""
    df = df.sort_values('timestamp').reset_index(drop=True)
    df = calculate_accurate_trades(df)
    
    # 누적 계산
    cumulative_buy_amount = 0
    cumulative_sell_amount = 0
    cumulative_buy_btc = 0
    cumulative_sell_btc = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # 누적 매수/매도 금액 및 수량
        cumulative_buy_amount += row['buy_amount']
        cumulative_sell_amount += row['sell_amount']
        
        if row['buy_amount'] > 0:
            cumulative_buy_btc += row['btc_traded']
        elif row['sell_amount'] > 0:
            cumulative_sell_btc += abs(row['btc_traded'])
        
        # 현재 자산 상태
        current_btc_value = row['btc_balance'] * row['btc_krw_price']
        current_krw = row['krw_balance']
        total_asset = current_btc_value + current_krw
        
        # 실현손익 계산 (DB의 btc_avg_buy_price 활용)
        if cumulative_sell_btc > 0 and row['btc_avg_buy_price'] > 0:
            # 매도한 BTC의 평균 매수가 기준 실현손익
            cost_of_sold_btc = cumulative_sell_btc * row['btc_avg_buy_price']
            realized_profit = cumulative_sell_amount - cost_of_sold_btc
        else:
            realized_profit = 0
        
        # 평가손익 계산 (현재 보유 BTC 기준)
        if row['btc_balance'] > 0 and row['btc_avg_buy_price'] > 0:
            cost_of_held_btc = row['btc_balance'] * row['btc_avg_buy_price']
            unrealized_profit = current_btc_value - cost_of_held_btc
        else:
            unrealized_profit = 0
        
        # 총 손익
        total_profit = realized_profit + unrealized_profit
        
        # 투자원금 계산 (순 투입 금액)
        net_investment = cumulative_buy_amount - cumulative_sell_amount
        
        # 수익률 계산
        if net_investment > 0:
            return_rate = (total_profit / net_investment) * 100
        else:
            return_rate = 0
        
        # 결과 저장
        df.loc[i, 'cumulative_buy_amount'] = cumulative_buy_amount
        df.loc[i, 'cumulative_sell_amount'] = cumulative_sell_amount
        df.loc[i, 'cumulative_buy_btc'] = cumulative_buy_btc
        df.loc[i, 'cumulative_sell_btc'] = cumulative_sell_btc
        df.loc[i, 'net_investment'] = net_investment
        df.loc[i, 'realized_profit'] = realized_profit
        df.loc[i, 'unrealized_profit'] = unrealized_profit
        df.loc[i, 'total_profit'] = total_profit
        df.loc[i, 'return_rate'] = return_rate
        df.loc[i, 'total_asset'] = total_asset
    
    # 일별 수익률
    df['daily_return'] = df['total_asset'].pct_change() * 100
    
    return df

# ============================================================================
# 차트 생성 함수들
# ============================================================================

def create_portfolio_chart(df):
    """포트폴리오 가치 변화 차트"""
    fig = px.line(df, x='timestamp', y='total_asset',
                  title='포트폴리오 총 가치 변화',
                  labels={'total_asset': '포트폴리오 가치 (KRW)', 'timestamp': '시간'})
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

def create_profit_breakdown_chart(df):
    """실현/평가손익 분석 차트"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['realized_profit'],
        mode='lines',
        name='실현손익',
        line=dict(color='green', width=2),
        fill='tonexty'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['unrealized_profit'],
        mode='lines',
        name='평가손익',
        line=dict(color='orange', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['total_profit'],
        mode='lines',
        name='총손익',
        line=dict(color='blue', width=3)
    ))
    
    fig.update_layout(
        title='손익 구성 변화',
        xaxis_title='시간',
        yaxis_title='손익 (KRW)',
        height=400
    )
    
    return fig

def create_avg_buy_price_chart(df):
    """평균 매수가 vs 현재가 비교 차트"""
    fig = go.Figure()
    
    # 현재 BTC 가격
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['btc_krw_price'],
        mode='lines',
        name='현재 BTC 가격',
        line=dict(color='orange', width=2)
    ))
    
    # 평균 매수가
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['btc_avg_buy_price'],
        mode='lines',
        name='평균 매수가',
        line=dict(color='blue', width=2, dash='dash')
    ))
    
    # 매수 포인트
    buy_trades = df[df['buy_amount'] > 0]
    if len(buy_trades) > 0:
        fig.add_trace(go.Scatter(
            x=buy_trades['timestamp'],
            y=buy_trades['btc_krw_price'],
            mode='markers',
            name='매수',
            marker=dict(color='green', size=8, symbol='triangle-up')
        ))
    
    # 매도 포인트
    sell_trades = df[df['sell_amount'] > 0]
    if len(sell_trades) > 0:
        fig.add_trace(go.Scatter(
            x=sell_trades['timestamp'],
            y=sell_trades['btc_krw_price'],
            mode='markers',
            name='매도',
            marker=dict(color='red', size=8, symbol='triangle-down')
        ))
    
    fig.update_layout(
        title='BTC 가격 vs 평균 매수가',
        xaxis_title='시간',
        yaxis_title='가격 (KRW)',
        height=500
    )
    
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

def create_asset_composition_chart(df):
    """자산 구성 비율 변화 차트"""
    df['btc_ratio'] = (df['btc_value'] / df['total_asset']) * 100
    df['krw_ratio'] = (df['krw_balance'] / df['total_asset']) * 100
    
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
        current_value = latest_trade['total_asset']
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
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write(f"**첫 거래일**: {df['timestamp'].min().strftime('%Y-%m-%d')}")
    with col2:
        st.write(f"**최근 거래일**: {df['timestamp'].max().strftime('%Y-%m-%d')}")
    with col3:
        trading_days = (df['timestamp'].max() - df['timestamp'].min()).days
        st.write(f"**거래 기간**: {trading_days}일")
    with col4:
        current_avg_price = latest_trade['btc_avg_buy_price']
        st.write(f"**평균 매수가**: {current_avg_price:,.0f} KRW")

    # 4. 포트폴리오 가치 차트
    st.header('💰 포트폴리오 가치 변화')
    fig_portfolio = create_portfolio_chart(df)
    st.plotly_chart(fig_portfolio, use_container_width=True)

    # 5. 수익률 및 손익 분석
    st.header('📊 수익률 & 손익 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_return = create_return_chart(df)
        st.plotly_chart(fig_return, use_container_width=True)
    
    with col2:
        fig_profit = create_profit_breakdown_chart(df)
        st.plotly_chart(fig_profit, use_container_width=True)

    # 6. 상세 투자 성과
    st.header('💹 상세 투자 성과')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📈 매수/매도 현황")
        total_buy = latest_trade['cumulative_buy_amount']
        total_sell = latest_trade['cumulative_sell_amount']
        
        st.metric("총 매수금액", f"{format_metric_text(total_buy)} KRW")
        st.metric("총 매도금액", f"{format_metric_text(total_sell)} KRW")
        st.metric("순투자금액", f"{format_metric_text(total_buy - total_sell)} KRW")
    
    with col2:
        st.subheader("💰 손익 분석")
        realized = latest_trade['realized_profit']
        unrealized = latest_trade['unrealized_profit']
        total = latest_trade['total_profit']
        
        st.metric("실현손익", f"{format_metric_text(realized)} KRW",
                 delta="확정됨" if realized != 0 else None)
        st.metric("평가손익", f"{format_metric_text(unrealized)} KRW",
                 delta="미실현" if unrealized != 0 else None)
        st.metric("총 손익", f"{format_metric_text(total)} KRW")
    
    with col3:
        st.subheader("📊 거래 통계")
        total_trades = len(df)
        buy_trades = len(df[df['buy_amount'] > 0])
        sell_trades = len(df[df['sell_amount'] > 0])
        
        st.metric("총 거래횟수", f"{total_trades}회")
        st.metric("매수 거래", f"{buy_trades}회")
        st.metric("매도 거래", f"{sell_trades}회")

    # 7. BTC 가격 분석
    st.header('📈 BTC 가격 & 평균 매수가 분석')
    fig_price_analysis = create_avg_buy_price_chart(df)
    st.plotly_chart(fig_price_analysis, use_container_width=True)
    
    # 현재 손익 상황 표시
    current_price = latest_trade['btc_krw_price']
    avg_buy_price = latest_trade['btc_avg_buy_price']
    price_diff_pct = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("현재 BTC 가격", f"{current_price:,.0f} KRW")
    with col2:
        st.metric("평균 매수가", f"{avg_buy_price:,.0f} KRW")
    with col3:
        st.metric("가격 차이", f"{price_diff_pct:.2f}%", 
                 delta=f"{current_price - avg_buy_price:,.0f} KRW")

    # 8. 거래 패턴 분석
    st.header('🎯 거래 패턴 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_decision = create_decision_pie_chart(df)
        st.plotly_chart(fig_decision, use_container_width=True)
    
    with col2:
        fig_monthly = create_monthly_trades_chart(df)
        st.plotly_chart(fig_monthly, use_container_width=True)

    # 9. 자산 구성 변화
    st.header('💎 자산 구성 변화')
    fig_composition = create_asset_composition_chart(df)
    st.plotly_chart(fig_composition, use_container_width=True)

    # 10. 거래 내역 (최신순)
    st.header('📜 거래 내역 (최신순)')
    display_columns = ['timestamp', 'decision', 'btc_krw_price', 'btc_avg_buy_price', 
                      'btc_balance', 'krw_balance', 'return_rate']
    
    available_columns = [col for col in display_columns if col in df.columns]
    if 'reason_kr' in df.columns:
        available_columns.append('reason_kr')
    elif 'reason' in df.columns:
        available_columns.append('reason')
    
    # 최신순으로 정렬하여 표시
    df_display = df.sort_values('timestamp', ascending=False)
    styled_df = df_display[available_columns].head(20)
    
    # 수익률 컬럼 포맷팅
    if 'return_rate' in styled_df.columns:
        styled_df = styled_df.copy()
        styled_df['return_rate'] = styled_df['return_rate'].apply(lambda x: f"{x:.2f}%")
    
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
        **평균 매수가**: {latest_trade['btc_avg_buy_price']:,.0f} KRW  
        """)
    
    with col2:
        st.success(f"""
        **현재 BTC 잔액**: {latest_trade['btc_balance']:.6f} BTC  
        **현재 KRW 잔액**: {latest_trade['krw_balance']:,.0f} KRW  
        **포트폴리오 가치**: {latest_trade['total_asset']:,.0f} KRW  
        **총 손익**: {latest_trade['total_profit']:,.0f} KRW  
        **순투자금액**: {latest_trade['net_investment']:,.0f} KRW  
        """)
    
    if 'reason_kr' in df.columns and pd.notna(latest_trade['reason_kr']):
        st.write(f"**거래 이유**: {latest_trade['reason_kr']}")
    elif 'reason' in df.columns and pd.notna(latest_trade['reason']):
        st.write(f"**거래 이유**: {latest_trade['reason']}")

if __name__ == "__main__":
    main()