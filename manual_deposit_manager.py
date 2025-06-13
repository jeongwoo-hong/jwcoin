import sqlite3
import pandas as pd
from datetime import datetime

def add_manual_deposit(amount, date_str=None, description="수동 추가"):
    """수동으로 입금 내역 추가 (안전한 기본값 사용)"""
    
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
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]
        
        print(f"\n📋 테이블 컬럼들: {columns}")
        
        # 안전한 기본값으로 새 레코드 생성
        new_values = {}
        
        for i, col_name in enumerate(columns):
            if col_name == 'id':
                # ID는 자동 증가이므로 None
                new_values[col_name] = None
                
            elif col_name == 'timestamp':
                # 입력된 시간 또는 현재 시간
                new_values[col_name] = timestamp
                
            elif col_name == 'decision':
                # 입금은 보유 상태로
                new_values[col_name] = 'hold'
                
            elif col_name == 'percentage':
                # 거래 비율은 0 (입금이므로 거래 아님)
                new_values[col_name] = 0
                
            elif col_name == 'reason':
                # 입금 이유
                new_values[col_name] = f'Manual deposit: {description}'
                
            elif col_name == 'btc_balance':
                # BTC 잔액은 그대로 유지
                new_values[col_name] = latest_trade[i]
                
            elif col_name == 'krw_balance':
                # KRW 잔액은 입금액만큼 증가
                new_values[col_name] = latest_trade[i] + amount
                
            elif col_name == 'btc_avg_buy_price':
                # 평균 매수가는 그대로 유지
                new_values[col_name] = latest_trade[i]
                
            elif col_name == 'btc_krw_price':
                # 현재 BTC 가격은 그대로 유지
                new_values[col_name] = latest_trade[i]
                
            elif col_name == 'reflection':
                # 거래 후 분석은 입금 관련 메모
                new_values[col_name] = f'Manual deposit of {amount:,} KRW added'
                
            else:
                # 기타 컬럼들은 이전 값 그대로 또는 적절한 기본값
                if latest_trade[i] is not None:
                    new_values[col_name] = latest_trade[i]
                else:
                    # 컬럼 타입에 따른 기본값
                    col_type = columns_info[i][2].upper()
                    if 'INTEGER' in col_type:
                        new_values[col_name] = 0
                    elif 'REAL' in col_type or 'FLOAT' in col_type:
                        new_values[col_name] = 0.0
                    elif 'TEXT' in col_type or 'VARCHAR' in col_type:
                        new_values[col_name] = ''
                    else:
                        new_values[col_name] = None
        
        # INSERT 쿼리 생성 및 실행
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?' for _ in columns])
        values_list = [new_values[col] for col in columns]
        
        query = f"INSERT INTO trades ({columns_str}) VALUES ({placeholders})"
        
        print(f"\n🔧 실행할 쿼리: {query}")
        print(f"📊 삽입할 값들:")
        for col, val in new_values.items():
            print(f"   {col}: {val}")
        
        cursor.execute(query, values_list)
        conn.commit()
        
        print(f"\n✅ 입금 내역이 성공적으로 추가되었습니다!")
        print(f"   이전 KRW 잔액: {latest_trade[columns.index('krw_balance')]:,}원")
        print(f"   새로운 KRW 잔액: {new_values['krw_balance']:,}원")
        print(f"   증가액: +{amount:,}원")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def add_manual_withdraw(amount, date_str=None, description="수동 추가"):
    """수동으로 출금 내역 추가 (안전한 기본값 사용)"""
    
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
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]
        
        # 출금 전 잔액 확인
        krw_balance_idx = columns.index('krw_balance')
        current_krw = latest_trade[krw_balance_idx]
        
        if current_krw < amount:
            print(f"⚠️  경고: 현재 KRW 잔액({current_krw:,}원)보다 출금액이 큽니다.")
            confirm = input("계속 진행하시겠습니까? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ 출금 추가가 취소되었습니다.")
                return
        
        # 안전한 기본값으로 새 레코드 생성
        new_values = {}
        
        for i, col_name in enumerate(columns):
            if col_name == 'id':
                new_values[col_name] = None
            elif col_name == 'timestamp':
                new_values[col_name] = timestamp
            elif col_name == 'decision':
                new_values[col_name] = 'hold'
            elif col_name == 'percentage':
                new_values[col_name] = 0
            elif col_name == 'reason':
                new_values[col_name] = f'Manual withdraw: {description}'
            elif col_name == 'btc_balance':
                new_values[col_name] = latest_trade[i]
            elif col_name == 'krw_balance':
                new_values[col_name] = latest_trade[i] - amount  # KRW 감소
            elif col_name == 'btc_avg_buy_price':
                new_values[col_name] = latest_trade[i]
            elif col_name == 'btc_krw_price':
                new_values[col_name] = latest_trade[i]
            elif col_name == 'reflection':
                new_values[col_name] = f'Manual withdraw of {amount:,} KRW processed'
            else:
                # 기타 컬럼들 안전 처리
                if latest_trade[i] is not None:
                    new_values[col_name] = latest_trade[i]
                else:
                    col_type = columns_info[i][2].upper()
                    if 'INTEGER' in col_type:
                        new_values[col_name] = 0
                    elif 'REAL' in col_type or 'FLOAT' in col_type:
                        new_values[col_name] = 0.0
                    elif 'TEXT' in col_type:
                        new_values[col_name] = ''
                    else:
                        new_values[col_name] = None
        
        # INSERT 실행
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?' for _ in columns])
        values_list = [new_values[col] for col in columns]
        
        query = f"INSERT INTO trades ({columns_str}) VALUES ({placeholders})"
        cursor.execute(query, values_list)
        conn.commit()
        
        print(f"\n✅ 출금 내역이 성공적으로 추가되었습니다!")
        print(f"   이전 KRW 잔액: {current_krw:,}원")
        print(f"   새로운 KRW 잔액: {new_values['krw_balance']:,}원")
        print(f"   감소액: -{amount:,}원")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

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