import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from googletrans import Translator

# 데이터베이스 연결 함수
def get_connection():
    return sqlite3.connect('bitcoin_trades.db')

# Google Translate를 사용한 번역 함수
@st.cache_data
def translate_reason(reason):
    if pd.isna(reason) or reason == '' or str(reason).strip() == '':
        return reason
    
    try:
        translator = Translator()
        # 영어를 한국어로 번역
        translated = translator.translate(str(reason), src='en', dest='ko')
        return translated.text
    except Exception as e:
        # 번역 실패 시 원본 반환
        st.warning(f"Translation failed for '{reason}': {str(e)}")
        return reason

# 데이터 로드 함수
def load_data():
    conn = get_connection()
    query = "SELECT * FROM trades ORDER BY timestamp DESC"  # 최신순으로 정렬
    df = pd.read_sql_query(query, conn)
    conn.close()
    
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
    
    # 번역 진행 상황 표시
    if 'reason' in df.columns and len(df) > 0:
        with st.spinner('거래 이유를 번역하는 중...'):
            # 거래 이유를 한국어로 번역 (캐시 사용으로 중복 번역 방지)
            df['reason_kr'] = df['reason'].apply(translate_reason)
    
    # 표시할 컬럼 선택
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