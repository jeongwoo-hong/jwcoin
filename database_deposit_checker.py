import sqlite3
import pandas as pd

def check_database_structure():
    """데이터베이스 구조 및 입출금 내역 확인"""
    
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🔍 데이터베이스 입출금 내역 확인")
        print("=" * 60)
        
        # 1. 모든 테이블 확인
        print("\n📋 1. 데이터베이스의 모든 테이블:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            print(f"   - {table[0]}")
        
        # 2. trades 테이블 구조 재확인
        print("\n🏗️  2. 'trades' 테이블 구조:")
        cursor.execute("PRAGMA table_info(trades);")
        columns_info = cursor.fetchall()
        
        print(f"{'순번':<4} {'컬럼명':<20} {'타입':<15} {'설명':<30}")
        print("-" * 75)
        
        column_descriptions = {
            'id': '거래 ID',
            'timestamp': '거래 시간',
            'decision': '거래 결정 (buy/sell/hold)',
            'percentage': '거래 비율',
            'reason': '거래 이유',
            'btc_balance': 'BTC 잔액',
            'krw_balance': 'KRW 잔액',
            'btc_avg_buy_price': '평균 매수가',
            'btc_krw_price': '현재 BTC 가격',
            'reflection': '거래 후 분석',
            'deposit_amount': '입금 금액',
            'withdraw_amount': '출금 금액',
            'cash_deposit': '현금 입금',
            'cash_withdraw': '현금 출금'
        }
        
        for col in columns_info:
            cid, name, data_type, notnull, default_val, pk = col
            desc = column_descriptions.get(name, '알 수 없음')
            print(f"{cid:<4} {name:<20} {data_type:<15} {desc:<30}")
        
        # 3. 입출금 관련 컬럼 확인
        print("\n💰 3. 입출금 관련 컬럼 확인:")
        existing_columns = [col[1] for col in columns_info]
        
        deposit_withdraw_columns = [
            'deposit_amount', 'withdraw_amount', 'cash_deposit', 
            'cash_withdraw', 'krw_deposit', 'krw_withdraw'
        ]
        
        found_columns = []
        for col in deposit_withdraw_columns:
            if col in existing_columns:
                found_columns.append(col)
                print(f"   ✅ {col} - 존재")
            else:
                print(f"   ❌ {col} - 없음")
        
        # 4. 입출금 데이터 샘플 확인
        if found_columns:
            print(f"\n📊 4. 입출금 데이터 샘플 ({', '.join(found_columns)}):")
            
            for col in found_columns:
                cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {col} IS NOT NULL AND {col} != 0")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    cursor.execute(f"SELECT {col}, timestamp FROM trades WHERE {col} IS NOT NULL AND {col} != 0 LIMIT 5")
                    samples = cursor.fetchall()
                    
                    print(f"\n   {col}:")
                    for amount, time in samples:
                        print(f"     {time}: {amount:,.0f}")
                else:
                    print(f"\n   {col}: 데이터 없음")
        else:
            print("\n❌ 입출금 관련 컬럼이 없습니다.")
        
        # 5. KRW 잔액 변화 패턴 분석 (입출금 추정)
        print("\n📈 5. KRW 잔액 변화 패턴 분석:")
        cursor.execute("""
            SELECT 
                timestamp, 
                krw_balance,
                LAG(krw_balance) OVER (ORDER BY timestamp) as prev_krw,
                krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change,
                decision
            FROM trades 
            ORDER BY timestamp 
            LIMIT 10
        """)
        
        krw_changes = cursor.fetchall()
        print("   시간                     현재KRW      이전KRW      변화량       거래결정")
        print("-" * 85)
        
        for row in krw_changes:
            timestamp, current_krw, prev_krw, change, decision = row
            if prev_krw is not None:
                print(f"   {timestamp:<20} {current_krw:>10,.0f} {prev_krw:>10,.0f} {change:>10,.0f} {decision}")
        
        # 6. 큰 KRW 변화 감지 (입출금 가능성)
        print("\n🔍 6. 큰 KRW 변화 감지 (입출금 가능성):")
        cursor.execute("""
            SELECT 
                timestamp,
                krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change,
                decision,
                krw_balance
            FROM trades 
            WHERE ABS(krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp)) > 100000
            AND decision NOT IN ('buy', 'sell')
            ORDER BY ABS(krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp)) DESC
            LIMIT 10
        """)
        
        large_changes = cursor.fetchall()
        if large_changes:
            print("   시간                     KRW변화        거래결정    현재잔액")
            print("-" * 65)
            for row in large_changes:
                timestamp, change, decision, balance = row
                if change is not None:
                    change_type = "입금" if change > 0 else "출금"
                    print(f"   {timestamp:<20} {change:>10,.0f} ({change_type})  {decision:<8} {balance:>10,.0f}")
        else:
            print("   큰 KRW 변화가 감지되지 않았습니다.")
        
        # 7. 추천 해결책
        print("\n💡 7. 입출금 추적 추천 방법:")
        if not found_columns:
            print("""
   현재 데이터베이스에 입출금 컬럼이 없습니다.
   
   해결책 1: 테이블에 컬럼 추가
   ALTER TABLE trades ADD COLUMN deposit_amount REAL DEFAULT 0;
   ALTER TABLE trades ADD COLUMN withdraw_amount REAL DEFAULT 0;
   
   해결책 2: KRW 잔액 변화 패턴으로 추정
   - 매수/매도가 아닌데 KRW가 크게 증가 → 입금
   - 매수/매도가 아닌데 KRW가 크게 감소 → 출금
   
   해결책 3: 별도 테이블 생성
   CREATE TABLE cash_flows (
       id INTEGER PRIMARY KEY,
       timestamp TEXT,
       type TEXT,  -- 'deposit' or 'withdraw'
       amount REAL,
       description TEXT
   );
            """)
        else:
            print("   ✅ 입출금 컬럼이 존재합니다. 이를 활용하여 정확한 수익률 계산 가능합니다.")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ 분석 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 오류: {e}")

# 실행
if __name__ == "__main__":
    check_database_structure()