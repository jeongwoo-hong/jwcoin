import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pyupbit
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
from supabase import create_client, Client

# 환경변수 로드
load_dotenv()

# ============================================================================
# 설정 및 상수
# ============================================================================

UPBIT_FEE_RATE = 0.0005  # 업비트 수수료율 0.05%

# ============================================================================
# Supabase 연결
# ============================================================================

@st.cache_resource
def get_supabase_client():
    """Supabase 클라이언트 생성"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    return create_client(url, key)

@st.cache_data(ttl=60)
def get_trades_from_supabase(start_date=None):
    """Supabase에서 거래 기록 조회"""
    supabase = get_supabase_client()
    if not supabase:
        return pd.DataFrame()

    try:
        query = supabase.table("trades").select("*").order("timestamp", desc=True)

        if start_date:
            query = query.gte("timestamp", start_date.isoformat())

        response = query.execute()

        if response.data:
            df = pd.DataFrame(response.data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Supabase 조회 실패: {e}")
        return pd.DataFrame()

# ============================================================================
# 업비트 API 연결
# ============================================================================

@st.cache_data(ttl=60)  # 1분 캐시
def get_upbit_connection():
    """업비트 API 연결"""
    access = os.getenv("UPBIT_ACCESS_KEY")
    secret = os.getenv("UPBIT_SECRET_KEY")
    
    if not access or not secret:
        st.error("업비트 API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return None
    
    try:
        upbit = pyupbit.Upbit(access, secret)
        return upbit
    except Exception as e:
        st.error(f"업비트 API 연결 실패: {e}")
        return None

@st.cache_data(ttl=300)  # 5분 캐시
def get_upbit_trades(market="KRW-BTC", count=500):
    """업비트 거래내역 조회"""
    upbit = get_upbit_connection()
    if not upbit:
        return pd.DataFrame()
    
    try:
        # 체결 내역 조회
        trades = upbit.get_order(market, state="done")
        
        if not trades:
            return pd.DataFrame()
        
        # DataFrame으로 변환
        df = pd.DataFrame(trades)
        
        # 필요한 컬럼만 선택 및 정리
        if not df.empty:
            # 날짜 컬럼 처리
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['updated_at'] = pd.to_datetime(df['updated_at'])
            
            # 숫자 컬럼 처리
            numeric_cols = ['volume', 'remaining_volume', 'reserved_fee', 'remaining_fee', 
                          'paid_fee', 'locked', 'executed_volume', 'trades_count', 'price']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 정렬
            df = df.sort_values('created_at', ascending=False)
        
        return df
        
    except Exception as e:
        st.error(f"거래내역 조회 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)  # 1분 캐시
def get_current_balance():
    """현재 잔고 조회"""
    upbit = get_upbit_connection()
    if not upbit:
        return None
    
    try:
        balances = upbit.get_balances()
        current_btc_price = pyupbit.get_current_price("KRW-BTC")
        
        # BTC, KRW 잔고 추출
        btc_balance = 0
        krw_balance = 0
        btc_avg_price = 0
        
        for balance in balances:
            if balance['currency'] == 'BTC':
                btc_balance = float(balance['balance'])
                btc_avg_price = float(balance['avg_buy_price'])
            elif balance['currency'] == 'KRW':
                krw_balance = float(balance['balance'])
        
        return {
            'btc_balance': btc_balance,
            'krw_balance': krw_balance,
            'btc_avg_price': btc_avg_price,
            'current_btc_price': current_btc_price,
            'btc_value': btc_balance * current_btc_price,
            'total_asset': btc_balance * current_btc_price + krw_balance
        }
        
    except Exception as e:
        st.error(f"잔고 조회 실패: {e}")
        return None

# ============================================================================
# 유틸리티 함수들
# ============================================================================

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

def format_side(side):
    """매수/매도 한글 변환"""
    if side == 'bid':
        return '매수'
    elif side == 'ask':
        return '매도'
    else:
        return side

def format_order_type(ord_type):
    """주문 타입 한글 변환"""
    type_map = {
        'limit': '지정가',
        'price': '시장가(매수)',
        'market': '시장가(매도)',
        'best': '최유리'
    }
    return type_map.get(ord_type, ord_type)

# ============================================================================
# 데이터 분석 함수
# ============================================================================

def analyze_trading_performance(trades_df, current_balance):
    """거래 성과 분석"""
    if trades_df.empty or not current_balance:
        return {}
    
    # 매수/매도 거래 분리
    buy_trades = trades_df[trades_df['side'] == 'bid']
    sell_trades = trades_df[trades_df['side'] == 'ask']
    
    # 총 매수/매도 금액
    total_buy_amount = (buy_trades['executed_volume'] * buy_trades['price']).sum() if not buy_trades.empty else 0
    total_sell_amount = (sell_trades['executed_volume'] * sell_trades['price']).sum() if not sell_trades.empty else 0
    
    # 총 수수료
    total_fees = trades_df['paid_fee'].sum()
    
    # 현재 BTC 보유량 및 가치
    current_btc = current_balance['btc_balance']
    current_btc_value = current_balance['btc_value']
    current_krw = current_balance['krw_balance']
    
    # 실현 손익 (매도한 것만)
    realized_profit = total_sell_amount - (len(sell_trades) * current_balance['btc_avg_price'] * sell_trades['executed_volume'].mean() if not sell_trades.empty else 0)
    
    # 미실현 손익 (현재 보유 BTC)
    if current_balance['btc_avg_price'] > 0:
        unrealized_profit = (current_balance['current_btc_price'] - current_balance['btc_avg_price']) * current_btc
    else:
        unrealized_profit = 0
    
    return {
        'total_trades': len(trades_df),
        'buy_trades': len(buy_trades),
        'sell_trades': len(sell_trades),
        'total_buy_amount': total_buy_amount,
        'total_sell_amount': total_sell_amount,
        'total_fees': total_fees,
        'realized_profit': realized_profit,
        'unrealized_profit': unrealized_profit,
        'total_profit': realized_profit + unrealized_profit,
        'current_btc': current_btc,
        'current_btc_value': current_btc_value,
        'current_krw': current_krw,
        'total_asset': current_balance['total_asset']
    }

# ============================================================================
# 차트 생성
# ============================================================================

def create_trading_timeline_chart(trades_df):
    """거래 타임라인 차트"""
    if trades_df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # 매수 거래
    buy_trades = trades_df[trades_df['side'] == 'bid']
    if not buy_trades.empty:
        fig.add_trace(go.Scatter(
            x=buy_trades['created_at'],
            y=buy_trades['price'],
            mode='markers',
            name='매수',
            marker=dict(
                color='blue',
                size=buy_trades['executed_volume'] * 1000,  # 볼륨에 따른 크기
                symbol='triangle-up',
                sizemode='area',
                sizeref=2.*max(buy_trades['executed_volume'])/50**2,
                sizemin=4
            ),
            text=buy_trades.apply(lambda x: f"매수<br>가격: {x['price']:,.0f}원<br>수량: {x['executed_volume']:.6f} BTC", axis=1),
            hovertemplate='%{text}<extra></extra>'
        ))
    
    # 매도 거래
    sell_trades = trades_df[trades_df['side'] == 'ask']
    if not sell_trades.empty:
        fig.add_trace(go.Scatter(
            x=sell_trades['created_at'],
            y=sell_trades['price'],
            mode='markers',
            name='매도',
            marker=dict(
                color='red',
                size=sell_trades['executed_volume'] * 1000,
                symbol='triangle-down',
                sizemode='area',
                sizeref=2.*max(sell_trades['executed_volume'])/50**2 if not sell_trades.empty else 1,
                sizemin=4
            ),
            text=sell_trades.apply(lambda x: f"매도<br>가격: {x['price']:,.0f}원<br>수량: {x['executed_volume']:.6f} BTC", axis=1),
            hovertemplate='%{text}<extra></extra>'
        ))
    
    # 현재 BTC 가격 라인
    current_price = pyupbit.get_current_price("KRW-BTC")
    fig.add_hline(y=current_price, line_dash="dash", line_color="orange", 
                  annotation_text=f"현재가: {current_price:,.0f}원")
    
    fig.update_layout(
        title='거래 내역 타임라인',
        xaxis_title='시간',
        yaxis_title='가격 (KRW)',
        height=500
    )
    
    return fig

def create_volume_chart(trades_df):
    """거래량 차트"""
    if trades_df.empty:
        return go.Figure()

    # 일별 거래량 집계
    trades_df['date'] = trades_df['created_at'].dt.date
    daily_volume = trades_df.groupby(['date', 'side']).agg({
        'executed_volume': 'sum',
        'price': 'mean'
    }).reset_index()

    fig = go.Figure()

    # 매수량
    buy_volume = daily_volume[daily_volume['side'] == 'bid']
    if not buy_volume.empty:
        fig.add_trace(go.Bar(
            x=buy_volume['date'],
            y=buy_volume['executed_volume'],
            name='매수량',
            marker_color='blue',
            opacity=0.7
        ))

    # 매도량
    sell_volume = daily_volume[daily_volume['side'] == 'ask']
    if not sell_volume.empty:
        fig.add_trace(go.Bar(
            x=sell_volume['date'],
            y=-sell_volume['executed_volume'],  # 음수로 표시
            name='매도량',
            marker_color='red',
            opacity=0.7
        ))

    fig.update_layout(
        title='일별 거래량',
        xaxis_title='날짜',
        yaxis_title='BTC 거래량',
        height=400,
        barmode='relative'
    )

    return fig

def create_asset_chart(trades_df):
    """자산 증감 차트 (총 자산 = KRW + BTC*가격)"""
    if trades_df.empty:
        return go.Figure()

    # 시간순 정렬
    df = trades_df.sort_values('timestamp').copy()

    # 총 자산 계산
    df['total_asset'] = df['krw_balance'] + df['btc_balance'] * df['btc_krw_price']

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['total_asset'],
        mode='lines+markers',
        name='총 자산',
        line=dict(color='#2E86AB', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.1)'
    ))

    # 시작점 기준선
    if len(df) > 0:
        initial_asset = df.iloc[0]['total_asset']
        fig.add_hline(
            y=initial_asset,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"시작: {initial_asset:,.0f}원"
        )

    fig.update_layout(
        title='자산 증감 추이',
        xaxis_title='시간',
        yaxis_title='총 자산 (KRW)',
        height=400,
        yaxis=dict(tickformat=',')
    )

    return fig

def create_profit_chart(trades_df):
    """실질 수익 차트 (시작점 대비 수익/손실)"""
    if trades_df.empty:
        return go.Figure()

    # 시간순 정렬
    df = trades_df.sort_values('timestamp').copy()

    # 총 자산 및 수익 계산
    df['total_asset'] = df['krw_balance'] + df['btc_balance'] * df['btc_krw_price']
    initial_asset = df.iloc[0]['total_asset']
    df['profit'] = df['total_asset'] - initial_asset
    df['profit_pct'] = (df['profit'] / initial_asset) * 100

    fig = go.Figure()

    # 색상: 수익이면 초록, 손실이면 빨강
    colors = ['#00C853' if p >= 0 else '#FF1744' for p in df['profit']]

    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['profit'],
        name='실질 수익',
        marker_color=colors,
        text=df['profit_pct'].apply(lambda x: f"{x:+.1f}%"),
        textposition='outside'
    ))

    # 0 기준선
    fig.add_hline(y=0, line_color="black", line_width=1)

    fig.update_layout(
        title='실질 수익 추이 (시작점 대비)',
        xaxis_title='시간',
        yaxis_title='수익/손실 (KRW)',
        height=400,
        yaxis=dict(tickformat=',')
    )

    return fig

# ============================================================================
# 메인 애플리케이션
# ============================================================================

def main():
    st.set_page_config(page_title="Upbit Trading Dashboard", layout="wide")

    # 헤더
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title('업비트 거래 대시보드')
    with col2:
        if st.button("새로고침", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col3:
        data_source = st.selectbox("데이터 소스", ["업비트 API", "Supabase", "통합"])

    # 사이드바: 시작일 설정
    st.sidebar.header("차트 설정")
    start_date = st.sidebar.date_input(
        "시작일",
        value=datetime.now() - timedelta(days=7),
        max_value=datetime.now()
    )
    start_datetime = datetime.combine(start_date, datetime.min.time())
    
    # 업비트 API 연결 확인
    upbit = get_upbit_connection()
    if not upbit:
        st.stop()
    
    # 현재 잔고 조회
    current_balance = get_current_balance()
    if not current_balance:
        st.warning("잔고 정보를 가져올 수 없습니다.")
        st.stop()
    
    # 거래 내역 조회
    if data_source in ["업비트 API", "통합"]:
        with st.spinner("업비트 거래내역 조회 중..."):
            trades_df = get_upbit_trades()
    else:
        trades_df = pd.DataFrame()
    
    # 성과 분석
    if not trades_df.empty:
        analysis = analyze_trading_performance(trades_df, current_balance)
    else:
        analysis = {}
        st.warning("거래 내역이 없습니다.")
    
    # 현재 상태 표시
    st.header('💰 현재 자산 현황')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "보유 BTC", 
            f"{current_balance['btc_balance']:.6f} BTC",
            help=f"평균 매수가: {current_balance['btc_avg_price']:,.0f}원"
        )
    
    with col2:
        st.metric(
            "BTC 가치", 
            f"{format_number(current_balance['btc_value'])} KRW",
            help=f"현재가: {current_balance['current_btc_price']:,.0f}원"
        )
    
    with col3:
        st.metric(
            "보유 현금", 
            f"{format_number(current_balance['krw_balance'])} KRW"
        )
    
    with col4:
        st.metric(
            "총 자산", 
            f"{format_number(current_balance['total_asset'])} KRW"
        )
    
    # 거래 성과
    if analysis:
        st.header('📊 거래 성과 분석')
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "총 거래 수", 
                f"{analysis['total_trades']}건",
                help=f"매수: {analysis['buy_trades']}건, 매도: {analysis['sell_trades']}건"
            )
        
        with col2:
            unrealized = analysis.get('unrealized_profit', 0)
            st.metric(
                "미실현 손익", 
                f"{format_number(unrealized)} KRW",
                delta=f"{unrealized:+,.0f}" if unrealized != 0 else None
            )
        
        with col3:
            realized = analysis.get('realized_profit', 0)
            st.metric(
                "실현 손익", 
                f"{format_number(realized)} KRW",
                delta=f"{realized:+,.0f}" if realized != 0 else None
            )
        
        with col4:
            st.metric(
                "총 수수료", 
                f"{format_number(analysis.get('total_fees', 0))} KRW"
            )
    
    # 차트
    if not trades_df.empty:
        st.header('거래 분석')

        col1, col2 = st.columns(2)

        with col1:
            timeline_chart = create_trading_timeline_chart(trades_df)
            st.plotly_chart(timeline_chart, use_container_width=True)

        with col2:
            volume_chart = create_volume_chart(trades_df)
            st.plotly_chart(volume_chart, use_container_width=True)

    # 자산 증감 / 실질 수익 차트 (Supabase 데이터)
    st.header('자산 및 수익 추이')
    st.caption(f"시작일: {start_date} 이후 데이터")

    supabase_trades = get_trades_from_supabase(start_datetime)

    if not supabase_trades.empty:
        col1, col2 = st.columns(2)

        with col1:
            asset_chart = create_asset_chart(supabase_trades)
            st.plotly_chart(asset_chart, use_container_width=True)

        with col2:
            profit_chart = create_profit_chart(supabase_trades)
            st.plotly_chart(profit_chart, use_container_width=True)

        # 요약 통계
        if len(supabase_trades) > 1:
            first_record = supabase_trades.sort_values('timestamp').iloc[0]
            last_record = supabase_trades.sort_values('timestamp').iloc[-1]

            initial_asset = first_record['krw_balance'] + first_record['btc_balance'] * first_record['btc_krw_price']
            final_asset = last_record['krw_balance'] + last_record['btc_balance'] * last_record['btc_krw_price']
            total_profit = final_asset - initial_asset
            profit_pct = (total_profit / initial_asset) * 100 if initial_asset > 0 else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("시작 자산", f"{initial_asset:,.0f}원")
            with col2:
                st.metric("현재 자산", f"{final_asset:,.0f}원")
            with col3:
                st.metric("총 수익", f"{total_profit:+,.0f}원", delta=f"{profit_pct:+.2f}%")
            with col4:
                st.metric("거래 횟수", f"{len(supabase_trades)}회")
    else:
        st.info("해당 기간의 거래 기록이 없습니다.")
    
    # 거래 내역 테이블
    if not trades_df.empty:
        st.header('📜 최근 거래 내역')

        # 표시할 컬럼 선택
        display_cols = ['created_at', 'side', 'ord_type', 'price', 'executed_volume', 'paid_fee', 'state']
        if all(col in trades_df.columns for col in display_cols):
            display_df = trades_df[display_cols].copy()

            # 컬럼명 한글화
            display_df.columns = ['거래시간', '구분', '주문타입', '체결가격', '체결수량', '수수료', '상태']

            # 데이터 포맷팅
            display_df['구분'] = display_df['구분'].apply(format_side)
            display_df['주문타입'] = display_df['주문타입'].apply(format_order_type)
            display_df['체결가격'] = display_df['체결가격'].apply(lambda x: f"{x:,.0f}원")
            display_df['체결수량'] = display_df['체결수량'].apply(lambda x: f"{x:.6f} BTC")
            display_df['수수료'] = display_df['수수료'].apply(lambda x: f"{x:,.0f}원")

            # 페이지네이션
            page_size = 20
            total_pages = max(1, (len(display_df) + page_size - 1) // page_size)

            if 'upbit_page' not in st.session_state:
                st.session_state.upbit_page = 1

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.session_state.upbit_page = st.number_input(
                    f'페이지 (총 {total_pages}페이지, {len(display_df)}건)',
                    min_value=1, max_value=total_pages, value=st.session_state.upbit_page,
                    key='upbit_page_input'
                )

            start_idx = (st.session_state.upbit_page - 1) * page_size
            end_idx = start_idx + page_size
            st.dataframe(display_df.iloc[start_idx:end_idx], use_container_width=True)
        else:
            st.dataframe(trades_df.head(20), use_container_width=True)
    
    # AI 트레이딩 기록 (Supabase)
    if data_source in ["Supabase", "통합"]:
        st.header('🤖 AI 트레이딩 기록')

        if not supabase_trades.empty:
            # 표시할 컬럼
            display_cols = ['timestamp', 'decision', 'percentage', 'reason', 'btc_balance', 'krw_balance']
            available_cols = [col for col in display_cols if col in supabase_trades.columns]

            ai_display_df = supabase_trades[available_cols].copy()
            ai_display_df.columns = ['시간', '결정', '비율(%)', '이유', 'BTC 잔고', 'KRW 잔고'][:len(available_cols)]

            # 페이지네이션
            ai_page_size = 20
            ai_total_pages = max(1, (len(ai_display_df) + ai_page_size - 1) // ai_page_size)

            if 'ai_page' not in st.session_state:
                st.session_state.ai_page = 1

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.session_state.ai_page = st.number_input(
                    f'페이지 (총 {ai_total_pages}페이지, {len(ai_display_df)}건)',
                    min_value=1, max_value=ai_total_pages, value=st.session_state.ai_page,
                    key='ai_page_input'
                )

            ai_start_idx = (st.session_state.ai_page - 1) * ai_page_size
            ai_end_idx = ai_start_idx + ai_page_size
            st.dataframe(ai_display_df.iloc[ai_start_idx:ai_end_idx], use_container_width=True)
        else:
            st.info("AI 트레이딩 기록이 없습니다.")
    
    # 요약 정보
    st.markdown("---")
    st.header('📋 요약')
    
    if current_balance['btc_balance'] > 0:
        avg_price = current_balance['btc_avg_price']
        current_price = current_balance['current_btc_price']
        profit_rate = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
        
        if profit_rate >= 0:
            st.success(f"""
            **🎉 현재 {profit_rate:.2f}%의 수익률을 기록하고 있습니다!**
            
            • 평균 매수가: {avg_price:,.0f}원
            • 현재 BTC 가격: {current_price:,.0f}원
            • 보유 수량: {current_balance['btc_balance']:.6f} BTC
            • BTC 가치: {current_balance['btc_value']:,.0f}원
            """)
        else:
            st.error(f"""
            **📉 현재 {abs(profit_rate):.2f}%의 손실을 기록하고 있습니다.**
            
            • 평균 매수가: {avg_price:,.0f}원
            • 현재 BTC 가격: {current_price:,.0f}원
            • 보유 수량: {current_balance['btc_balance']:.6f} BTC
            • BTC 가치: {current_balance['btc_value']:,.0f}원
            """)
    else:
        st.info("현재 BTC를 보유하고 있지 않습니다.")

if __name__ == "__main__":
    main()