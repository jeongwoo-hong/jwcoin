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

def format_metric_text(value, max_length=12):
    """메트릭 텍스트의 길이를 자동으로 조절"""
    if pd.isna(value):
        return "0"
    
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

def translate_reason(reason):
    """거래 이유 한국어 번역"""
    if pd.isna(reason) or reason == '':
        return reason
    
    translations = {
        'RSI oversold': 'RSI 과매도',
        'RSI overbought': 'RSI 과매수', 
        'MACD bullish crossover': 'MACD 상승 교차',
        'MACD bearish crossover': 'MACD 하락 교차',
        'Breaking resistance': '저항선 돌파',
        'Breaking support': '지지선 이탈',
        'Risk management': '리스크 관리',
        'Profit taking': '수익 실현',
        'Stop loss': '손절매',
        'Technical analysis': '기술적 분석',
        'Market sentiment': '시장 심리'
    }
    
    for eng, kor in translations.items():
        if eng.lower() in str(reason).lower():
            return str(reason).replace(eng, kor)
    
    return reason

# ============================================================================
# 데이터 로드 및 기본 처리
# ============================================================================

@st.cache_data
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
        df['reason_kr'] = df['reason'].apply(translate_reason)
    
    return df

# ============================================================================
# 투자 성과 계산
# ============================================================================

def calculate_trading_amounts(df):
    """BTC 잔액 변화를 통한 매수/매도 금액 및 수수료 계산"""
    df = df.copy().reset_index(drop=True)
    
    # 초기화
    df['buy_amount'] = 0.0
    df['sell_amount'] = 0.0
    df['btc_traded'] = 0.0
    df['trading_fee'] = 0.0
    
    for i in range(len(df)):
        if i == 0:
            # 첫 거래 - 초기 BTC 보유량을 매수한 것으로 가정
            if df.loc[i, 'btc_balance'] > 0:
                buy_amount = df.loc[i, 'btc_balance'] * df.loc[i, 'btc_krw_price']
                df.loc[i, 'buy_amount'] = buy_amount
                df.loc[i, 'trading_fee'] = buy_amount * UPBIT_FEE_RATE
                df.loc[i, 'btc_traded'] = df.loc[i, 'btc_balance']
        else:
            # BTC 잔액 변화로 거래량 계산
            btc_diff = df.loc[i, 'btc_balance'] - df.loc[i-1, 'btc_balance']
            
            if btc_diff > 0:  # 매수
                buy_amount = btc_diff * df.loc[i, 'btc_krw_price']
                df.loc[i, 'buy_amount'] = buy_amount
                df.loc[i, 'trading_fee'] = buy_amount * UPBIT_FEE_RATE
                df.loc[i, 'btc_traded'] = btc_diff
                
            elif btc_diff < 0:  # 매도
                sell_amount = abs(btc_diff) * df.loc[i, 'btc_krw_price']
                df.loc[i, 'sell_amount'] = sell_amount
                df.loc[i, 'trading_fee'] = sell_amount * UPBIT_FEE_RATE
                df.loc[i, 'btc_traded'] = btc_diff
    
    return df

def calculate_performance_metrics(df):
    """수수료를 반영한 투자 성과 계산"""
    df = df.copy()
    
    # 누적 값들 초기화
    df['cumulative_buy_amount'] = df['buy_amount'].cumsum()
    df['cumulative_sell_amount'] = df['sell_amount'].cumsum()
    df['cumulative_fees'] = df['trading_fee'].cumsum()
    
    # 포트폴리오 가치
    df['btc_value'] = df['btc_balance'] * df['btc_krw_price']
    df['total_value'] = df['btc_value'] + df['krw_balance']
    
    # 각 시점별 성과 계산
    for i in range(len(df)):
        # 투자원금 (매수금액 - 매도금액 + 수수료)
        net_investment = df.loc[i, 'cumulative_buy_amount'] - df.loc[i, 'cumulative_sell_amount'] + df.loc[i, 'cumulative_fees']
        df.loc[i, 'net_investment'] = max(net_investment, 0.01)  # 0으로 나누기 방지
        
        # 순투자금액 (수수료 제외)
        pure_investment = df.loc[i, 'cumulative_buy_amount'] - df.loc[i, 'cumulative_sell_amount']
        df.loc[i, 'pure_investment'] = max(pure_investment, 0.01)
        
        # 실현손익 (매도를 통한 확정 손익)
        if df.loc[i, 'cumulative_sell_amount'] > 0 and df.loc[i, 'btc_avg_buy_price'] > 0:
            sell_btc_amount = df.loc[i, 'cumulative_sell_amount'] / df.loc[i, 'btc_krw_price']
            cost_of_sold_btc = sell_btc_amount * df.loc[i, 'btc_avg_buy_price']
            realized_profit = df.loc[i, 'cumulative_sell_amount'] - cost_of_sold_btc
        else:
            realized_profit = 0
        df.loc[i, 'realized_profit'] = realized_profit
        
        # 평가손익 (현재 보유 BTC의 미실현 손익)
        if df.loc[i, 'btc_balance'] > 0 and df.loc[i, 'btc_avg_buy_price'] > 0:
            cost_of_held_btc = df.loc[i, 'btc_balance'] * df.loc[i, 'btc_avg_buy_price']
            unrealized_profit = df.loc[i, 'btc_value'] - cost_of_held_btc
        else:
            unrealized_profit = 0
        df.loc[i, 'unrealized_profit'] = unrealized_profit
        
        # 총 손익 (수수료 반영 전후)
        total_profit_before_fees = realized_profit + unrealized_profit
        total_profit_after_fees = total_profit_before_fees - df.loc[i, 'cumulative_fees']
        
        df.loc[i, 'total_profit_before_fees'] = total_profit_before_fees
        df.loc[i, 'total_profit_after_fees'] = total_profit_after_fees
        
        # 수익률 계산
        return_rate = (total_profit_after_fees / df.loc[i, 'net_investment']) * 100
        return_rate_excluding_fees = (total_profit_before_fees / df.loc[i, 'pure_investment']) * 100
        
        df.loc[i, 'return_rate'] = return_rate
        df.loc[i, 'return_rate_excluding_fees'] = return_rate_excluding_fees
    
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

def create_return_comparison_chart(df):
    """수수료 반영 전후 수익률 비교"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['return_rate'],
        mode='lines',
        name='실제 수익률 (수수료 반영)',
        line=dict(color='blue', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['return_rate_excluding_fees'],
        mode='lines',
        name='수수료 제외 수익률',
        line=dict(color='green', width=2, dash='dash')
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7)
    
    fig.update_layout(
        title='수익률 비교: 수수료 반영 전후',
        xaxis_title='시간',
        yaxis_title='수익률 (%)',
        height=400
    )
    
    return fig

def create_fee_analysis_chart(df):
    """수수료 분석 차트"""
    fig = go.Figure()
    
    # 누적 수수료
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['cumulative_fees'],
        mode='lines',
        name='누적 수수료',
        line=dict(color='red', width=2),
        fill='tozeroy'
    ))
    
    fig.update_layout(
        title='누적 거래 수수료',
        xaxis_title='시간',
        yaxis_title='누적 수수료 (KRW)',
        height=400
    )
    
    return fig

def create_profit_breakdown_chart(df):
    """손익 분해 차트"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['realized_profit'],
        mode='lines',
        name='실현손익',
        line=dict(color='green', width=2)
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
        y=df['total_profit_after_fees'],
        mode='lines',
        name='총손익(수수료반영)',
        line=dict(color='blue', width=3)
    ))
    
    fig.update_layout(
        title='손익 구성 분석',
        xaxis_title='시간',
        yaxis_title='손익 (KRW)',
        height=400
    )
    
    return fig

def create_price_analysis_chart(df):
    """BTC 가격 분석 차트"""
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
    buy_data = df[df['buy_amount'] > 0]
    if len(buy_data) > 0:
        fig.add_trace(go.Scatter(
            x=buy_data['timestamp'],
            y=buy_data['btc_krw_price'],
            mode='markers',
            name='매수',
            marker=dict(color='green', size=8, symbol='triangle-up')
        ))
    
    # 매도 포인트
    sell_data = df[df['sell_amount'] > 0]
    if len(sell_data) > 0:
        fig.add_trace(go.Scatter(
            x=sell_data['timestamp'],
            y=sell_data['btc_krw_price'],
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
    """거래 결정 분포"""
    decision_counts = df['decision'].value_counts()
    fig = px.pie(values=decision_counts.values, names=decision_counts.index, 
                 title='거래 결정 분포', hole=0.4)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

# ============================================================================
# 메인 애플리케이션
# ============================================================================

def main():
    st.set_page_config(page_title="Bitcoin Trading Dashboard", layout="wide")
    st.title('🚀 Bitcoin Trading Dashboard')
    st.markdown("---")

    # 데이터 로드
    df = load_data()
    
    if len(df) == 0:
        st.warning("거래 데이터가 없습니다.")
        return

    # 데이터 처리
    df = calculate_trading_amounts(df)
    df = calculate_performance_metrics(df)
    
    if len(df) == 0:
        st.error("데이터 처리 중 오류가 발생했습니다.")
        return
    
    latest = df.iloc[-1]  # 최신 데이터

    # 핵심 지표
    st.header('📈 핵심 투자 지표')
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        value = latest['total_value']
        st.metric("포트폴리오 가치", f"{format_metric_text(value)} KRW")
    
    with col2:
        rate = latest['return_rate']
        st.metric("수익률(수수료반영)", f"{format_metric_text(rate):.2f}%",
                 delta=f"{rate:.2f}%" if rate != 0 else None)
    
    with col3:
        profit = latest['total_profit_after_fees']
        st.metric("순손익", f"{format_metric_text(profit)} KRW",
                 delta=f"{profit:,.0f} KRW" if profit != 0 else None)
    
    with col4:
        fees = latest['cumulative_fees']
        st.metric("누적 수수료", f"{format_metric_text(fees)} KRW")
    
    with col5:
        investment = latest['net_investment']
        st.metric("투자원금", f"{format_metric_text(investment)} KRW")
    
    with col6:
        btc = latest['btc_balance']
        st.metric("보유 BTC", f"{format_metric_text(btc):.6f} BTC")

    st.markdown("---")

    # 기본 정보
    st.header('📋 거래 기간 정보')
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.write(f"**첫 거래일**: {df['timestamp'].min().strftime('%Y-%m-%d')}")
    with col2:
        st.write(f"**최근 거래일**: {df['timestamp'].max().strftime('%Y-%m-%d')}")
    with col3:
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        st.write(f"**거래 기간**: {days}일")
    with col4:
        avg_price = latest['btc_avg_buy_price']
        st.write(f"**평균 매수가**: {avg_price:,.0f} KRW")

    # 포트폴리오 가치 차트
    st.header('💰 포트폴리오 가치 변화')
    fig_portfolio = create_portfolio_chart(df)
    st.plotly_chart(fig_portfolio, use_container_width=True)

    # 수익률 및 수수료 분석
    st.header('📊 수익률 & 수수료 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_return = create_return_comparison_chart(df)
        st.plotly_chart(fig_return, use_container_width=True)
    
    with col2:
        fig_fee = create_fee_analysis_chart(df)
        st.plotly_chart(fig_fee, use_container_width=True)

    # 손익 상세 분석
    st.header('💰 손익 상세 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_profit = create_profit_breakdown_chart(df)
        st.plotly_chart(fig_profit, use_container_width=True)
    
    with col2:
        fig_decision = create_decision_pie_chart(df)
        st.plotly_chart(fig_decision, use_container_width=True)

    # 상세 투자 성과
    st.header('💹 상세 투자 성과')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📈 매수/매도 현황")
        buy_total = latest['cumulative_buy_amount']
        sell_total = latest['cumulative_sell_amount']
        
        st.metric("총 매수금액", f"{format_metric_text(buy_total)} KRW")
        st.metric("총 매도금액", f"{format_metric_text(sell_total)} KRW")
        st.metric("순거래금액", f"{format_metric_text(buy_total - sell_total)} KRW")
    
    with col2:
        st.subheader("💸 수수료 분석")
        total_fees = latest['cumulative_fees']
        pure_inv = latest['pure_investment']
        fee_rate = (total_fees / pure_inv * 100) if pure_inv > 0 else 0
        
        st.metric("총 수수료", f"{format_metric_text(total_fees)} KRW")
        st.metric("수수료율", f"{fee_rate:.3f}%")
        
        trade_count = len(df[df['trading_fee'] > 0])
        avg_fee = total_fees / trade_count if trade_count > 0 else 0
        st.metric("거래당 평균수수료", f"{format_metric_text(avg_fee)} KRW")
    
    with col3:
        st.subheader("💰 손익 비교")
        profit_before = latest['total_profit_before_fees']
        profit_after = latest['total_profit_after_fees']
        
        st.metric("수수료 제외 손익", f"{format_metric_text(profit_before)} KRW")
        st.metric("수수료 반영 손익", f"{format_metric_text(profit_after)} KRW")
        st.metric("수수료 영향", f"-{format_metric_text(total_fees)} KRW")

    # BTC 가격 분석
    st.header('📈 BTC 가격 분석')
    fig_price = create_price_analysis_chart(df)
    st.plotly_chart(fig_price, use_container_width=True)
    
    # 현재 가격 vs 평균 매수가
    current_price = latest['btc_krw_price']
    avg_buy_price = latest['btc_avg_buy_price']
    price_diff = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("현재 BTC 가격", f"{current_price:,.0f} KRW")
    with col2:
        st.metric("평균 매수가", f"{avg_buy_price:,.0f} KRW")
    with col3:
        st.metric("가격 차이", f"{price_diff:.2f}%", 
                 delta=f"{current_price - avg_buy_price:,.0f} KRW")

    # 거래 내역
    st.header('📜 거래 내역 (최신순)')
    
    display_cols = ['timestamp', 'decision', 'btc_krw_price', 'btc_avg_buy_price', 
                   'btc_balance', 'krw_balance', 'trading_fee', 'return_rate']
    
    available_cols = [col for col in display_cols if col in df.columns]
    if 'reason_kr' in df.columns:
        available_cols.append('reason_kr')
    elif 'reason' in df.columns:
        available_cols.append('reason')
    
    df_display = df.sort_values('timestamp', ascending=False)[available_cols].head(20)
    
    # 포맷팅
    if 'return_rate' in df_display.columns:
        df_display = df_display.copy()
        df_display['return_rate'] = df_display['return_rate'].apply(lambda x: f"{x:.2f}%")
    if 'trading_fee' in df_display.columns:
        df_display['trading_fee'] = df_display['trading_fee'].apply(lambda x: f"{x:,.0f}")
    
    st.dataframe(df_display, use_container_width=True)

    # 실시간 성과 요약
    st.header('🎯 실시간 성과 요약')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **최근 거래 결정**: {latest['decision']}  
        **거래 시간**: {latest['timestamp']}  
        **BTC 가격**: {latest['btc_krw_price']:,.0f} KRW  
        **수익률(수수료반영)**: {latest['return_rate']:.2f}%  
        **수익률(수수료제외)**: {latest['return_rate_excluding_fees']:.2f}%  
        """)
    
    with col2:
        st.success(f"""
        **현재 BTC 잔액**: {latest['btc_balance']:.6f} BTC  
        **현재 KRW 잔액**: {latest['krw_balance']:,.0f} KRW  
        **포트폴리오 가치**: {latest['total_value']:,.0f} KRW  
        **순손익(수수료반영)**: {latest['total_profit_after_fees']:,.0f} KRW  
        **총 거래수수료**: {latest['cumulative_fees']:,.0f} KRW  
        """)
    
    if 'reason_kr' in df.columns and pd.notna(latest['reason_kr']):
        st.write(f"**거래 이유**: {latest['reason_kr']}")
    elif 'reason' in df.columns and pd.notna(latest['reason']):
        st.write(f"**거래 이유**: {latest['reason']}")

if __name__ == "__main__":
    main()