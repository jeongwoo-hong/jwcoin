import sqlite3
import pandas as pd
from datetime import datetime

def add_manual_deposit(amount, date_str=None, description="수동 추가"):
    """수동으로 입금 내역 추가"""
    
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        cursor = conn.cursor()
        
        # 날짜 설정 (없으면 현재 시간)
        if date_str:
            timestamp = date_str
        else:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"💰 수동 입금 내역 추가 중...")
        print(f"   금액: {amount:,}원")
        print(f"   시간: {timestamp}")
        print(f"   설명: {description}")
        
        # 현재 최신 거래 정보 가져오기
        cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 1")
        latest_trade = cursor.fetchone()
        
        if not latest_trade:
            print("❌ 기존 거래 데이터가 없습니다.")
            return
        
        # 컬럼명 가져오기
        cursor.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"\n📋 사용 가능한 컬럼들: {columns}")
        
        # 새 레코드 생성 (기존 데이터 복사 + KRW만 증가)
        new_record = list(latest_trade)
        
        # ID 제거 (자동 생성)
        new_record[0] = None
        
        # 컬럼 인덱스 찾기
        timestamp_idx = columns.index('timestamp')
        btc_balance_idx = columns.index('btc_balance')
        krw_balance_idx = columns.index('krw_balance')
        decision_idx = columns.index('decision')
        reason_idx = columns.index('reason')
        
        # 새 값 설정
        new_record[timestamp_idx] = timestamp
        new_record[krw_balance_idx] = latest_trade[krw_balance_idx] + amount  # KRW 증가
        new_record[decision_idx] = 'hold'  # 입금은 보유로 설정
        new_record[reason_idx] = f'Manual deposit: {description}'
        
        # INSERT 쿼리 생성
        placeholders = ', '.join(['?' for _ in range(len(columns))])
        query = f"INSERT INTO trades ({', '.join(columns)}) VALUES ({placeholders})"
        
        # 실행
        cursor.execute(query, new_record)
        conn.commit()
        
        print(f"✅ 입금 내역이 성공적으로 추가되었습니다!")
        print(f"   이전 KRW 잔액: {latest_trade[krw_balance_idx]:,}원")
        print(f"   새로운 KRW 잔액: {new_record[krw_balance_idx]:,}원")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def add_manual_withdraw(amount, date_str=None, description="수동 추가"):
    """수동으로 출금 내역 추가"""
    
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        cursor = conn.cursor()
        
        if date_str:
            timestamp = date_str
        else:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"💸 수동 출금 내역 추가 중...")
        print(f"   금액: {amount:,}원")
        print(f"   시간: {timestamp}")
        print(f"   설명: {description}")
        
        cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 1")
        latest_trade = cursor.fetchone()
        
        if not latest_trade:
            print("❌ 기존 거래 데이터가 없습니다.")
            return
        
        cursor.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cursor.fetchall()]
        
        new_record = list(latest_trade)
        new_record[0] = None  # ID 제거
        
        timestamp_idx = columns.index('timestamp')
        krw_balance_idx = columns.index('krw_balance')
        decision_idx = columns.index('decision')
        reason_idx = columns.index('reason')
        
        # 출금 검증
        if latest_trade[krw_balance_idx] < amount:
            print(f"⚠️  경고: 현재 KRW 잔액({latest_trade[krw_balance_idx]:,}원)보다 출금액이 큽니다.")
            confirm = input("계속 진행하시겠습니까? (y/n): ")
            if confirm.lower() != 'y':
                print("❌ 출금 추가가 취소되었습니다.")
                return
        
        new_record[timestamp_idx] = timestamp
        new_record[krw_balance_idx] = latest_trade[krw_balance_idx] - amount  # KRW 감소
        new_record[decision_idx] = 'hold'
        new_record[reason_idx] = f'Manual withdraw: {description}'
        
        placeholders = ', '.join(['?' for _ in range(len(columns))])
        query = f"INSERT INTO trades ({', '.join(columns)}) VALUES ({placeholders})"
        
        cursor.execute(query, new_record)
        conn.commit()
        
        print(f"✅ 출금 내역이 성공적으로 추가되었습니다!")
        print(f"   이전 KRW 잔액: {latest_trade[krw_balance_idx]:,}원")
        print(f"   새로운 KRW 잔액: {new_record[krw_balance_idx]:,}원")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def show_recent_trades():
    """최근 거래 내역 확인"""
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        
        print("\n📋 최근 10개 거래 내역:")
        df = pd.read_sql_query("""
            SELECT timestamp, decision, reason, btc_balance, krw_balance 
            FROM trades 
            ORDER BY timestamp DESC 
            LIMIT 10
        """, conn)
        
        print(df.to_string(index=False))
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류: {e}")

def detect_missing_deposits():
    """누락된 입금 추정"""
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        
        print("\n🔍 KRW 잔액 급증 구간 분석 (누락 입금 가능성):")
        
        df = pd.read_sql_query("""
            SELECT 
                timestamp,
                krw_balance,
                LAG(krw_balance) OVER (ORDER BY timestamp) as prev_krw,
                krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change,
                decision,
                reason
            FROM trades 
            ORDER BY timestamp
        """, conn)
        
        # 큰 KRW 증가 찾기
        large_increases = df[
            (df['krw_change'] > 100000) & 
            (~df['decision'].isin(['buy', 'sell']))
        ].copy()
        
        if len(large_increases) > 0:
            print("   의심스러운 KRW 증가 구간:")
            print("   시간                     증가금액      결정    이유")
            print("-" * 70)
            
            for _, row in large_increases.iterrows():
                print(f"   {row['timestamp']:<20} +{row['krw_change']:>8,.0f}원   {row['decision']:<6} {row['reason']}")
        else:
            print("   큰 KRW 증가 구간이 발견되지 않았습니다.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류: {e}")

# 메인 실행 부분
if __name__ == "__main__":
    print("=" * 60)
    print("💰 수동 입출금 내역 관리 도구")
    print("=" * 60)
    
    while True:
        print("\n📋 메뉴:")
        print("1. 입금 내역 추가")
        print("2. 출금 내역 추가")
        print("3. 최근 거래 내역 확인")
        print("4. 누락된 입금 추정")
        print("5. 종료")
        
        choice = input("\n선택하세요 (1-5): ").strip()
        
        if choice == "1":
            print("\n💰 입금 내역 추가")
            amount = float(input("입금 금액을 입력하세요: "))
            date_input = input("날짜 입력 (YYYY-MM-DD HH:MM:SS, 엔터시 현재시간): ").strip()
            date_str = date_input if date_input else None
            desc = input("설명 (선택사항): ").strip() or "수동 추가 입금"
            
            add_manual_deposit(amount, date_str, desc)
            
        elif choice == "2":
            print("\n💸 출금 내역 추가")
            amount = float(input("출금 금액을 입력하세요: "))
            date_input = input("날짜 입력 (YYYY-MM-DD HH:MM:SS, 엔터시 현재시간): ").strip()
            date_str = date_input if date_input else None
            desc = input("설명 (선택사항): ").strip() or "수동 추가 출금"
            
            add_manual_withdraw(amount, date_str, desc)
            
        elif choice == "3":
            show_recent_trades()
            
        elif choice == "4":
            detect_missing_deposits()
            
        elif choice == "5":
            print("👋 프로그램을 종료합니다.")
            break
            
        else:
            print("❌ 잘못된 선택입니다.")

    # 빠른 실행 (500,000원 입금 추가)
    print("\n" + "="*60)
    print("🚀 빠른 실행: 500,000원 입금 추가")
    print("="*60)
    add_manual_deposit(500000, None, "누락된 입금 복구")