import sqlite3
import pandas as pd

def check_recent_deposits():
    """최근 입금 내역 및 데이터베이스 상태 확인"""
    
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🔍 입금 내역 확인")
        print("=" * 60)
        
        # 1. 최근 10개 거래 확인
        print("\n📋 최근 10개 거래 내역:")
        cursor.execute("""
            SELECT timestamp, decision, reason, krw_balance, 
                   LAG(krw_balance) OVER (ORDER BY timestamp) as prev_krw,
                   krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change
            FROM trades 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        recent_trades = cursor.fetchall()
        
        print(f"{'시간':<20} {'결정':<6} {'KRW변화':<10} {'KRW잔액':<12} {'이유'}")
        print("-" * 80)
        
        for trade in recent_trades:
            timestamp, decision, reason, krw_balance, prev_krw, krw_change = trade
            change_str = f"+{krw_change:,.0f}" if krw_change and krw_change > 0 else f"{krw_change:,.0f}" if krw_change else "0"
            reason_short = (reason[:30] + "...") if reason and len(reason) > 30 else (reason or "")
            print(f"{timestamp:<20} {decision:<6} {change_str:<10} {krw_balance:>12,.0f} {reason_short}")
        
        # 2. 500,000원 관련 변화 찾기
        print(f"\n🔍 500,000원 관련 변화 찾기:")
        cursor.execute("""
            SELECT timestamp, decision, reason, krw_balance,
                   krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change
            FROM trades 
            WHERE ABS(krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp)) = 500000
            ORDER BY timestamp DESC
        """)
        
        deposit_500k = cursor.fetchall()
        
        if deposit_500k:
            print("   500,000원 변화가 발견되었습니다:")
            for trade in deposit_500k:
                timestamp, decision, reason, krw_balance, krw_change = trade
                change_type = "입금" if krw_change > 0 else "출금"
                print(f"   {timestamp} | {change_type} 500,000원 | {reason}")
        else:
            print("   ❌ 500,000원 변화가 발견되지 않았습니다.")
        
        # 3. Manual deposit 관련 항목 찾기
        print(f"\n🔍 Manual deposit 관련 항목:")
        cursor.execute("""
            SELECT timestamp, decision, reason, krw_balance
            FROM trades 
            WHERE reason LIKE '%Manual deposit%' OR reason LIKE '%수동%'
            ORDER BY timestamp DESC
        """)
        
        manual_deposits = cursor.fetchall()
        
        if manual_deposits:
            print("   수동 입금 관련 항목이 발견되었습니다:")
            for trade in manual_deposits:
                timestamp, decision, reason, krw_balance = trade
                print(f"   {timestamp} | KRW: {krw_balance:,}원 | {reason}")
        else:
            print("   ❌ 수동 입금 관련 항목이 없습니다.")
        
        # 4. 데이터베이스 무결성 확인
        print(f"\n🔧 데이터베이스 상태:")
        cursor.execute("SELECT COUNT(*) FROM trades")
        total_count = cursor.fetchone()[0]
        print(f"   총 거래 수: {total_count}개")
        
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM trades")
        date_range = cursor.fetchone()
        print(f"   기간: {date_range[0]} ~ {date_range[1]}")
        
        # 5. 권장 조치
        print(f"\n💡 권장 조치:")
        if not deposit_500k and not manual_deposits:
            print("   ✅ 500,000원 입금이 추가되지 않았습니다.")
            print("   🚀 다음 명령어로 안전하게 추가하세요:")
            print("      python quick_deposit_fix.py")
        else:
            print("   ⚠️  500,000원 관련 항목이 이미 있습니다.")
            print("   🔍 중복 추가를 피하기 위해 확인이 필요합니다.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def check_database_health():
    """데이터베이스 건강성 검사"""
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        cursor = conn.cursor()
        
        print(f"\n🏥 데이터베이스 건강성 검사:")
        
        # 타임스탬프 형식 확인
        cursor.execute("SELECT timestamp FROM trades ORDER BY timestamp DESC LIMIT 5")
        timestamps = cursor.fetchall()
        
        print("   최근 타임스탬프 형식:")
        for i, (ts,) in enumerate(timestamps):
            print(f"     {i+1}. {ts} (길이: {len(ts)})")
        
        # 중복 확인
        cursor.execute("""
            SELECT timestamp, COUNT(*) 
            FROM trades 
            GROUP BY timestamp 
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"   ⚠️  중복된 타임스탬프: {len(duplicates)}개")
        else:
            print(f"   ✅ 중복된 타임스탬프 없음")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 건강성 검사 오류: {e}")

if __name__ == "__main__":
    check_recent_deposits()
    check_database_health()
    
    print("\n" + "=" * 60)
    print("✅ 확인 완료!")
    print("=" * 60)