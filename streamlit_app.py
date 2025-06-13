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
    
    try:
        num = float(value)
        
        # 작은 소수의 경우 (BTC 등)
        if 0 < abs(num) < 1:
            return f"{num:.6f}"
        
        # 큰 숫자의 경우 단위 변환
        if abs(num) >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif abs(num) >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif abs(num) >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            # 일반 숫자의 경우
            if abs(num) >= 100:
                return f"{num:,.0f}"
            else:
                return f"{num:.2f}"
                
    except (ValueError, TypeError):
        # 문자열인 경우 줄임
        text = str(value)
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

def load_data():
    """데이터베이스에서 거래 데이터 로드 (실시간 업데이트)"""
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

def calculate_realized_profit(df):
    """실현이익 중심 계산"""
    df = df.copy()
    df = calculate_trading_amounts(df)
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # 현재 자산 가치
        current_btc_value = row['btc_balance'] * row['btc_krw_price']
        current_krw = row['krw_balance']
        total_asset_value = current_btc_value + current_krw
        
        # 누적 매수/매도 금액 및 수수료
        cumulative_buy = df['buy_amount'][:i+1].sum()
        cumulative_sell = df['sell_amount'][:i+1].sum()
        cumulative_fees = df['trading_fee'][:i+1].sum()
        
        # 실현이익 = 매도금액 - 매도한 BTC의 평균 매수가 - 수수료
        if cumulative_sell > 0 and row['btc_avg_buy_price'] > 0:
            # 매도한 BTC 수량 계산
            sold_btc_amount = cumulative_sell / row['btc_krw_price'] if row['btc_krw_price'] > 0 else 0
            # 매도한 BTC의 원가 (평균 매수가 기준)
            cost_of_sold_btc = sold_btc_amount * row['btc_avg_buy_price']
            # 실현이익 = 매도금액 - 원가
            realized_profit = cumulative_sell - cost_of_sold_btc
        else:
            realized_profit = 0
        
        # 매도 관련 수수료만 차감 (실제 실현이익에서)
        sell_fees = df['trading_fee'][:i+1][df['sell_amount'][:i+1] > 0].sum()
        realized_profit_after_fees = realized_profit - sell_fees
        
        # 순투자금액 (현재 투입되어 있는 돈)
        net_investment = cumulative_buy - cumulative_sell + cumulative_fees
        
        # 보유 BTC 평가액 (참고용)
        if row['btc_balance'] > 0 and row['btc_avg_buy_price'] > 0:
            held_btc_cost = row['btc_balance'] * row['btc_avg_buy_price']
            unrealized_profit = current_btc_value - held_btc_cost
        else:
            unrealized_profit = 0
        
        # 결과 저장
        df.loc[i, 'total_asset_value'] = total_asset_value
        df.loc[i, 'net_investment'] = net_investment
        df.loc[i, 'realized_profit'] = realized_profit
        df.loc[i, 'realized_profit_after_fees'] = realized_profit_after_fees
        df.loc[i, 'unrealized_profit'] = unrealized_profit
        df.loc[i, 'cumulative_buy'] = cumulative_buy
        df.loc[i, 'cumulative_sell'] = cumulative_sell
        df.loc[i, 'cumulative_fees'] = cumulative_fees
        
        # 실현 수익률
        if cumulative_sell > 0:
            realized_return_rate = (realized_profit_after_fees / cumulative_sell) * 100
        else:
            realized_return_rate = 0
        df.loc[i, 'realized_return_rate'] = realized_return_rate
    
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

def create_realized_profit_chart(df):
    """실현이익 변화 차트"""
    fig = go.Figure()
    
    # 실현이익 라인
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['realized_profit_after_fees'],
        mode='lines',
        name='실현이익',
        line=dict(color='green', width=3),
        fill='tozeroy'
    ))
    
    # 0선 표시
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7)
    
    fig.update_layout(
        title='실현이익 누적 변화',
        xaxis_title='시간',
        yaxis_title='실현이익 (KRW)',
        height=400
    )
    
    return fig

def create_trading_volume_chart(df):
    """매수/매도 거래량 차트"""
    fig = go.Figure()
    
    # 매수 거래량
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['cumulative_buy'],
        mode='lines',
        name='누적 매수금액',
        line=dict(color='blue', width=2)
    ))
    
    # 매도 거래량
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['cumulative_sell'],
        mode='lines',
        name='누적 매도금액',
        line=dict(color='orange', width=2)
    ))
    
    fig.update_layout(
        title='누적 매수/매도 금액',
        xaxis_title='시간',
        yaxis_title='거래금액 (KRW)',
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
    
    # 헤더와 새로고침 버튼
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title('🚀 Bitcoin Trading Dashboard')
    with col2:
        if st.button("🔄 새로고침", type="primary"):
            st.rerun()
    
    st.markdown("---")

    # 데이터 로드 (실시간)
    df = load_data()
    
    if len(df) == 0:
        st.warning("거래 데이터가 없습니다.")
        return

    # 데이터 처리
    df = calculate_trading_amounts(df)
    df = calculate_realized_profit(df)
    
    if len(df) == 0:
        st.error("데이터 처리 중 오류가 발생했습니다.")
        return
    
    latest = df.iloc[-1]  # 최신 데이터
    
    # 최신 업데이트 정보 표시
    st.info(f"📊 최신 거래: {latest['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | 총 거래: {len(df)}개")

    # 핵심 지표 (실현이익 중심)
    st.header('💰 실현이익 현황')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        realized_profit = latest['realized_profit_after_fees']
        profit_color = "normal" if realized_profit >= 0 else "inverse"
        status = "실현이익" if realized_profit >= 0 else "실현손실"
        st.metric(status, f"{format_metric_text(abs(realized_profit))} KRW",
                 delta=f"{realized_profit:,.0f} KRW")
    
    with col2:
        sell_amount = latest['cumulative_sell']
        st.metric("총 매도금액", f"{format_metric_text(sell_amount)} KRW")
    
    with col3:
        realized_rate = latest['realized_return_rate']
        st.metric("실현 수익률", f"{realized_rate:.2f}%",
                 delta=f"{realized_rate:.2f}%")
    
    with col4:
        total_fees = latest['cumulative_fees']
        st.metric("총 거래수수료", f"{format_metric_text(total_fees)} KRW")

    # 현재 보유 자산 현황
    st.markdown("---")
    st.header('📋 현재 보유 자산')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        asset_value = latest['total_asset_value']
        st.metric("현재 자산가치", f"{format_metric_text(asset_value)} KRW")
    
    with col2:
        btc_amount = latest['btc_balance']
        st.metric("보유 BTC", f"{format_metric_text(btc_amount)} BTC")
    
    with col3:
        krw_amount = latest['krw_balance']
        st.metric("보유 현금", f"{format_metric_text(krw_amount)} KRW")
    
    with col4:
        unrealized = latest['unrealized_profit']
        status = "평가이익" if unrealized >= 0 else "평가손실"
        st.metric(f"{status} (미실현)", f"{format_metric_text(abs(unrealized))} KRW")

    st.markdown("---")

    st.markdown("---")

    # 핵심 차트들
    st.header('📊 실현이익 분석')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_realized = create_realized_profit_chart(df)
        st.plotly_chart(fig_realized, use_container_width=True)
    
    with col2:
        fig_trading = create_trading_volume_chart(df)
        st.plotly_chart(fig_trading, use_container_width=True)

    # 거래 성과 요약
    st.header('💼 거래 성과 요약')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_buy = latest['cumulative_buy']
        st.metric("총 매수금액", f"{format_metric_text(total_buy)} KRW")
        
        total_sell = latest['cumulative_sell']
        st.metric("총 매도금액", f"{format_metric_text(total_sell)} KRW")
    
    with col2:
        # 거래 수익성 분석
        if latest['cumulative_sell'] > 0:
            trading_efficiency = (latest['realized_profit_after_fees'] / latest['cumulative_sell']) * 100
            st.metric("매도 거래 효율성", f"{trading_efficiency:.2f}%")
        else:
            st.metric("매도 거래 효율성", "0.00%")
        
        trade_count = len(df[df['sell_amount'] > 0])
        st.metric("매도 거래 횟수", f"{trade_count}회")
    
    with col3:
        # BTC 가격 정보
        current_price = latest['btc_krw_price']
        avg_price = latest['btc_avg_buy_price']
        price_diff = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
        
        st.metric("현재 BTC 가격", f"{current_price:,.0f} KRW")
        st.metric("평균 매수가", f"{avg_price:,.0f} KRW")
        st.metric("가격 차이", f"{price_diff:.2f}%")

    # 최근 거래 내역
    st.header('📜 최근 거래 내역')
    
    display_cols = ['timestamp', 'decision', 'btc_krw_price', 'btc_balance', 'realized_profit_after_fees']
    available_cols = [col for col in display_cols if col in df.columns]
    
    df_display = df.sort_values('timestamp', ascending=False)[available_cols].head(10)
    
    # 포맷팅
    if 'realized_profit_after_fees' in df_display.columns:
        df_display = df_display.copy()
        df_display['realized_profit_after_fees'] = df_display['realized_profit_after_fees'].apply(
            lambda x: f"{x:,.0f} KRW" if x != 0 else "-"
        )
    
    st.dataframe(df_display, use_container_width=True)

    # 최종 실현이익 요약
    st.header('🎯 실현이익 요약')
    
    realized_profit = latest['realized_profit_after_fees']
    
    if realized_profit > 0:
        st.success(f"""
        **🎉 실현이익이 발생했습니다!**
        
        **실현이익**: {realized_profit:,.0f} KRW  
        **총 매도금액**: {latest['cumulative_sell']:,.0f} KRW  
        **실현 수익률**: {latest['realized_return_rate']:.2f}%  
        **매도 거래 효율**: {(realized_profit/latest['cumulative_sell']*100):.2f}%  
        """)
    elif realized_profit < 0:
        st.error(f"""
        **📉 실현손실이 발생했습니다.**
        
        **실현손실**: {abs(realized_profit):,.0f} KRW  
        **총 매도금액**: {latest['cumulative_sell']:,.0f} KRW  
        **실현 손실률**: {latest['realized_return_rate']:.2f}%  
        """)
    else:
        st.info(f"""
        **💼 아직 매도 거래가 없습니다.**
        
        **현재 보유 BTC**: {latest['btc_balance']:.6f} BTC  
        **평가이익**: {latest['unrealized_profit']:,.0f} KRW  
        **현재 자산가치**: {latest['total_asset_value']:,.0f} KRW  
        """)
    
    if 'reason' in df.columns and pd.notna(latest['reason']):
        st.write(f"**최근 거래 이유**: {latest['reason']}")

if __name__ == "__main__":
    main()