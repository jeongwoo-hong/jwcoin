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
    """데이터베이스에서 거래 데이터 로드 (안전한 날짜 파싱)"""
    conn = get_connection()
    query = "SELECT * FROM trades ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) == 0:
        return df
    
    # 안전한 날짜 파싱
    try:
        # 여러 날짜 형식 처리
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
        
        # 파싱에 실패한 행들 확인
        invalid_dates = df[df['timestamp'].isna()]
        if len(invalid_dates) > 0:
            print(f"⚠️ 날짜 파싱 실패한 행: {len(invalid_dates)}개")
            # 실패한 행들은 현재 시간으로 대체
            df.loc[df['timestamp'].isna(), 'timestamp'] = pd.Timestamp.now()
            
    except Exception as e:
        print(f"날짜 파싱 오류: {e}")
        # 모든 날짜를 현재 시간으로 설정 (최후 수단)
        df['timestamp'] = pd.Timestamp.now()
    
    return df

def detect_cash_flows(df):
    """입출금 감지 (수동 추가 데이터 포함)"""
    df = df.copy().reset_index(drop=True)
    df['cash_flow_type'] = 'trade'
    df['deposit_amount'] = 0.0
    df['withdraw_amount'] = 0.0
    
    for i in range(len(df)):
        current_reason = str(df.loc[i, 'reason']).lower() if pd.notna(df.loc[i, 'reason']) else ''
        
        # 수동 입금/출금 감지 (reason 컬럼 확인)
        if 'manual deposit' in current_reason:
            df.loc[i, 'cash_flow_type'] = 'deposit'
            # KRW 변화량으로 입금액 계산
            if i > 0:
                krw_change = df.loc[i, 'krw_balance'] - df.loc[i-1, 'krw_balance']
                if krw_change > 0:
                    df.loc[i, 'deposit_amount'] = krw_change
            else:
                # 첫 번째 행인 경우, reason에서 금액 추출 시도
                import re
                amount_match = re.search(r'(\d{1,3}(?:,\d{3})*)', current_reason)
                if amount_match:
                    df.loc[i, 'deposit_amount'] = float(amount_match.group(1).replace(',', ''))
            continue
        
        elif 'manual withdraw' in current_reason:
            df.loc[i, 'cash_flow_type'] = 'withdraw'
            # KRW 변화량으로 출금액 계산
            if i > 0:
                krw_change = df.loc[i-1, 'krw_balance'] - df.loc[i, 'krw_balance']
                if krw_change > 0:
                    df.loc[i, 'withdraw_amount'] = krw_change
            continue
        
        # 자동 감지 (BTC 변화 없고 KRW만 변화)
        if i > 0:
            prev_btc = df.loc[i-1, 'btc_balance']
            curr_btc = df.loc[i, 'btc_balance']
            prev_krw = df.loc[i-1, 'krw_balance']
            curr_krw = df.loc[i, 'krw_balance']
            
            btc_change = abs(curr_btc - prev_btc)
            krw_change = curr_krw - prev_krw
            
            # BTC 변화 없고 KRW만 변화 = 입출금
            if btc_change < 0.00001 and abs(krw_change) > 1000:
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
    
    # 헤더 + 수동 입출금 관리
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title('🚀 Bitcoin Investment Dashboard')
    with col2:
        if st.button("🔄 새로고침", type="primary"):
            st.rerun()
    with col3:
        if st.button("💰 입출금 관리"):
            st.session_state.show_manual_manager = True
    
    # 수동 입출금 관리 UI
    if st.session_state.get('show_manual_manager', False):
        st.markdown("---")
        st.header('💰 수동 입출금 관리')
        
        tab1, tab2, tab3 = st.tabs(["입금 추가", "출금 추가", "내역 확인"])
        
        with tab1:
            st.subheader("📥 입금 내역 추가")
            
            col1, col2 = st.columns(2)
            with col1:
                deposit_amount = st.number_input("입금 금액 (원)", min_value=0, value=500000, step=1000)
                deposit_desc = st.text_input("설명", value="누락된 입금 복구")
            
            with col2:
                use_custom_date = st.checkbox("특정 날짜 지정")
                if use_custom_date:
                    deposit_date = st.date_input("날짜")
                    deposit_time = st.time_input("시간")
                    deposit_datetime = f"{deposit_date} {deposit_time}"
                else:
                    deposit_datetime = None
            
            if st.button("✅ 입금 추가", type="primary"):
                try:
                    # 데이터베이스에 입금 내역 추가
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # 최신 거래 정보 가져오기
                    cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 1")
                    latest_trade = cursor.fetchone()
                    
                    if latest_trade:
                        # 컬럼명 가져오기
                        cursor.execute("PRAGMA table_info(trades)")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        # 새 레코드 생성
                        new_record = list(latest_trade)
                        new_record[0] = None  # ID 자동 생성
                        
                        # 인덱스 찾기
                        timestamp_idx = columns.index('timestamp')
                        krw_balance_idx = columns.index('krw_balance')
                        decision_idx = columns.index('decision')
                        reason_idx = columns.index('reason')
                        
                        # 새 값 설정
                        if deposit_datetime:
                            new_record[timestamp_idx] = deposit_datetime
                        else:
                            from datetime import datetime
                            new_record[timestamp_idx] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        new_record[krw_balance_idx] = latest_trade[krw_balance_idx] + deposit_amount
                        new_record[decision_idx] = 'hold'
                        new_record[reason_idx] = f'Manual deposit: {deposit_desc}'
                        
                        # 삽입
                        placeholders = ', '.join(['?' for _ in range(len(columns))])
                        query = f"INSERT INTO trades ({', '.join(columns)}) VALUES ({placeholders})"
                        cursor.execute(query, new_record)
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ {deposit_amount:,}원 입금 내역이 추가되었습니다!")
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 오류 발생: {e}")
        
        with tab2:
            st.subheader("📤 출금 내역 추가")
            
            col1, col2 = st.columns(2)
            with col1:
                withdraw_amount = st.number_input("출금 금액 (원)", min_value=0, value=100000, step=1000)
                withdraw_desc = st.text_input("설명 ", value="수동 추가 출금")
            
            with col2:
                use_custom_date2 = st.checkbox("특정 날짜 지정 ")
                if use_custom_date2:
                    withdraw_date = st.date_input("날짜 ")
                    withdraw_time = st.time_input("시간 ")
                    withdraw_datetime = f"{withdraw_date} {withdraw_time}"
                else:
                    withdraw_datetime = None
            
            if st.button("✅ 출금 추가", type="secondary"):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 1")
                    latest_trade = cursor.fetchone()
                    
                    if latest_trade:
                        cursor.execute("PRAGMA table_info(trades)")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        krw_balance_idx = columns.index('krw_balance')
                        
                        # 잔액 확인
                        if latest_trade[krw_balance_idx] < withdraw_amount:
                            st.warning(f"⚠️ 현재 KRW 잔액({latest_trade[krw_balance_idx]:,}원)이 부족합니다.")
                            if not st.checkbox("강제 실행"):
                                st.stop()
                        
                        new_record = list(latest_trade)
                        new_record[0] = None
                        
                        timestamp_idx = columns.index('timestamp')
                        decision_idx = columns.index('decision')
                        reason_idx = columns.index('reason')
                        
                        if withdraw_datetime:
                            new_record[timestamp_idx] = withdraw_datetime
                        else:
                            from datetime import datetime
                            new_record[timestamp_idx] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        new_record[krw_balance_idx] = latest_trade[krw_balance_idx] - withdraw_amount
                        new_record[decision_idx] = 'hold'
                        new_record[reason_idx] = f'Manual withdraw: {withdraw_desc}'
                        
                        placeholders = ', '.join(['?' for _ in range(len(columns))])
                        query = f"INSERT INTO trades ({', '.join(columns)}) VALUES ({placeholders})"
                        cursor.execute(query, new_record)
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ {withdraw_amount:,}원 출금 내역이 추가되었습니다!")
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 오류 발생: {e}")
        
        with tab3:
            st.subheader("📋 최근 입출금 의심 내역")
            
            try:
                conn = get_connection()
                # KRW 변화 큰 구간 찾기
                df_check = pd.read_sql_query("""
                    SELECT 
                        timestamp,
                        krw_balance,
                        LAG(krw_balance) OVER (ORDER BY timestamp) as prev_krw,
                        krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change,
                        decision,
                        reason
                    FROM trades 
                    ORDER BY timestamp DESC
                    LIMIT 20
                """, conn)
                conn.close()
                
                # 큰 변화 필터링
                big_changes = df_check[
                    (abs(df_check['krw_change']) > 50000) & 
                    (df_check['krw_change'].notna())
                ]
                
                if len(big_changes) > 0:
                    st.write("**큰 KRW 변화가 있었던 거래들:**")
                    
                    display_df = big_changes[['timestamp', 'krw_change', 'decision', 'reason']].copy()
                    display_df['krw_change'] = display_df['krw_change'].apply(
                        lambda x: f"+{x:,.0f}원" if x > 0 else f"{x:,.0f}원"
                    )
                    display_df.columns = ['시간', 'KRW 변화', '결정', '이유']
                    
                    st.dataframe(display_df, use_container_width=True)
                else:
                    st.info("큰 KRW 변화가 감지되지 않았습니다.")
                    
            except Exception as e:
                st.error(f"오류: {e}")
        
        if st.button("❌ 관리 창 닫기"):
            st.session_state.show_manual_manager = False
            st.rerun()
        
        st.markdown("---")
    
    # 기존 대시보드 내용...

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
    
    st.dataframe(df_display.sort_values('시간', ascending=False), _container_width=True)
    # st.dataframe(df_display.sort_values('시간', ascending=False).head(15), _container_width=True)

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