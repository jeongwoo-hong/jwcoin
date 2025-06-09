import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# 데이터베이스 연결 함수
def get_connection():
    return sqlite3.connect('bitcoin_trades.db')

# 거래 이유 한국어 번역 함수
def translate_reason(reason):
    if pd.isna(reason) or reason == '':
        return reason
    
    translations = {
        # 기술적 분석 관련
        'RSI oversold': 'RSI 과매도',
        'RSI overbought': 'RSI 과매수',
        'MACD bullish crossover': 'MACD 상승 교차',
        'MACD bearish crossover': 'MACD 하락 교차',
        'Moving average golden cross': '이동평균 골든크로스',
        'Moving average death cross': '이동평균 데드크로스',
        'Bollinger band squeeze': '볼린저 밴드 수축',
        'Breaking resistance': '저항선 돌파',
        'Breaking support': '지지선 이탈',
        'Volume surge': '거래량 급증',
        'Price momentum up': '가격 모멘텀 상승',
        'Price momentum down': '가격 모멘텀 하락',
        
        # 시장 상황 관련
        'Market trend bullish': '시장 상승 추세',
        'Market trend bearish': '시장 하락 추세',
        'High volatility': '높은 변동성',
        'Low volatility': '낮은 변동성',
        'Fear and greed index': '공포탐욕지수',
        'Market correction': '시장 조정',
        'Bull market': '상승장',
        'Bear market': '하락장',
        
        # 뉴스/이벤트 관련
        'Positive news': '긍정적 뉴스',
        'Negative news': '부정적 뉴스',
        'Regulatory news': '규제 관련 뉴스',
        'Institutional buying': '기관 매수',
        'Whale movement': '고래 움직임',
        
        # 포트폴리오 관리
        'Risk management': '리스크 관리',
        'Profit taking': '수익 실현',
        'Stop loss': '손절매',
        'Portfolio rebalancing': '포트폴리오 리밸런싱',
        'Dollar cost averaging': '정액 분할 매수',
        
        # 일반적인 이유
        'Technical analysis': '기술적 분석',
        'Fundamental analysis': '기본적 분석',
        'Market sentiment': '시장 심리',
        'Price target reached': '목표가 도달',
        'Strong support level': '강한 지지선',
        'Strong resistance level': '강한 저항선'
    }
    
    # 완전 일치 먼저 확인
    if reason in translations:
        return translations[reason]
    
    # 부분 일치 확인 (대소문자 구분 없이)
    reason_lower = reason.lower()
    for eng, kor in translations.items():
        if eng.lower() in reason_lower:
            return reason.replace(eng, kor)
    
    return reason  # 번역되지 않은 경우 원본 반환

# 데이터 로드 함수
def load_data():
    conn = get_connection()
    query = "SELECT * FROM trades ORDER BY timestamp DESC"  # 최신순으로 정렬
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # 거래 이유를 한국어로 번역
    if 'reason' in df.columns:
        df['reason_kr'] = df['reason'].apply(translate_reason)
    
    return df

# 메인 함수
def main():
    st.title('Bitcoin Trades Viewer')

    # 데이터 로드
    df = load_data()

    # 기본 통계
    st.header('Basic Statistics')
    st.write(f"Total number of trades: {len(df)}")
    st.write(f"First trade date: {df['timestamp'].min()}")
    st.write(f"Last trade date: {df['timestamp'].max()}")

    # 거래 내역 표시 (최신순)
    st.header('Trade History (Latest First)')
    # 표시할 컬럼 선택 (한국어 reason 포함)
    display_columns = ['timestamp', 'decision', 'btc_krw_price', 'btc_balance', 'krw_balance']
    
    # 컬럼이 존재하는지 확인하고 표시
    available_columns = [col for col in display_columns if col in df.columns]
    if 'reason_kr' in df.columns:
        available_columns.append('reason_kr')
    elif 'reason' in df.columns:
        available_columns.append('reason')
    
    st.dataframe(df[available_columns])

    # 거래 결정 분포
    st.header('Trade Decision Distribution')
    decision_counts = df['decision'].value_counts()
    fig = px.pie(values=decision_counts.values, names=decision_counts.index, title='거래 결정 분포')
    st.plotly_chart(fig)

    # BTC 잔액 변화 (시간순으로 정렬하여 차트 표시)
    st.header('BTC Balance Over Time')
    df_sorted = df.sort_values('timestamp')  # 차트용으로는 시간순 정렬
    fig = px.line(df_sorted, x='timestamp', y='btc_balance', title='BTC Balance')
    st.plotly_chart(fig)

    # KRW 잔액 변화
    st.header('KRW Balance Over Time')
    fig = px.line(df_sorted, x='timestamp', y='krw_balance', title='KRW Balance')
    st.plotly_chart(fig)

    # BTC 가격 변화
    st.header('BTC Price Over Time')
    fig = px.line(df_sorted, x='timestamp', y='btc_krw_price', title='BTC Price (KRW)')
    st.plotly_chart(fig)

    # 최근 거래 요약
    st.header('Recent Trade Summary')
    if len(df) > 0:
        latest_trade = df.iloc[0]
        st.write(f"**최근 거래 결정**: {latest_trade['decision']}")
        st.write(f"**거래 시간**: {latest_trade['timestamp']}")
        st.write(f"**BTC 가격**: {latest_trade['btc_krw_price']:,.0f} KRW")
        st.write(f"**현재 BTC 잔액**: {latest_trade['btc_balance']:.6f} BTC")
        st.write(f"**현재 KRW 잔액**: {latest_trade['krw_balance']:,.0f} KRW")
        
        if 'reason_kr' in df.columns and pd.notna(latest_trade['reason_kr']):
            st.write(f"**거래 이유**: {latest_trade['reason_kr']}")
        elif 'reason' in df.columns and pd.notna(latest_trade['reason']):
            st.write(f"**거래 이유**: {latest_trade['reason']}")

if __name__ == "__main__":
    main()