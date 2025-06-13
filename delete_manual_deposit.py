import sqlite3
import pandas as pd

def delete_manual_deposit_records():
    """수동 입금 관련 모든 거래 내역 삭제"""
    
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🗑️  수동 입금 내역 삭제 작업")
        print("=" * 60)
        
        # 1. 삭제 대상 확인
        print("\n🔍 삭제 대상 확인:")
        
        # Manual deposit 관련 기록 찾기
        cursor.execute("""
            SELECT id, timestamp, reason, krw_balance,
                   krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change
            FROM trades 
            WHERE reason LIKE '%Manual deposit%' OR reason LIKE '%수동%'
            ORDER BY timestamp DESC
        """)
        
        manual_records = cursor.fetchall()
        
        if manual_records:
            print("   발견된 수동 입금 기록:")
            print(f"   {'ID':<5} {'시간':<25} {'KRW변화':<12} {'KRW잔액':<12} {'이유'}")
            print("   " + "-" * 80)
            
            total_to_delete = 0
            for record in manual_records:
                id_val, timestamp, reason, krw_balance, krw_change = record
                change_str = f"+{krw_change:,.0f}" if krw_change and krw_change > 0 else f"{krw_change:,.0f}" if krw_change else "0"
                reason_short = (reason[:35] + "...") if reason and len(reason) > 35 else (reason or "")
                print(f"   {id_val:<5} {timestamp:<25} {change_str:<12} {krw_balance:>12,.0f} {reason_short}")
                total_to_delete += 1
            
            print(f"\n   📊 삭제될 기록 수: {total_to_delete}개")
        else:
            print("   ❌ 삭제할 수동 입금 기록이 없습니다.")
            conn.close()
            return
        
        # 2. 삭제 전 백업 정보
        print(f"\n💾 삭제 전 상태:")
        cursor.execute("SELECT COUNT(*) FROM trades")
        total_before = cursor.fetchone()[0]
        
        cursor.execute("SELECT krw_balance FROM trades ORDER BY timestamp DESC LIMIT 1")
        current_krw = cursor.fetchone()[0]
        
        print(f"   총 거래 기록: {total_before}개")
        print(f"   현재 KRW 잔액: {current_krw:,}원")
        
        # 3. 확인 메시지
        print(f"\n⚠️  정말로 {total_to_delete}개의 수동 입금 기록을 삭제하시겠습니까?")
        print("   이 작업은 되돌릴 수 없습니다!")
        
        # 스크립트에서는 자동 진행
        confirm = "y"
        print(f"   확인: {confirm}")
        
        if confirm.lower() in ['y', 'yes']:
            # 4. 삭제 실행
            print(f"\n🗑️  삭제 실행 중...")
            
            cursor.execute("""
                DELETE FROM trades 
                WHERE reason LIKE '%Manual deposit%' OR reason LIKE '%수동%'
            """)
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"   ✅ {deleted_count}개 기록이 삭제되었습니다!")
            
            # 5. 삭제 후 상태 확인
            print(f"\n📊 삭제 후 상태:")
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_after = cursor.fetchone()[0]
            
            cursor.execute("SELECT krw_balance FROM trades ORDER BY timestamp DESC LIMIT 1")
            new_krw = cursor.fetchone()[0]
            
            print(f"   총 거래 기록: {total_after}개 (이전: {total_before}개)")
            print(f"   현재 KRW 잔액: {new_krw:,}원 (이전: {current_krw:,}원)")
            print(f"   KRW 잔액 변화: {new_krw - current_krw:+,}원")
            
            # 6. 최근 거래 내역 확인
            print(f"\n📋 삭제 후 최근 5개 거래:")
            cursor.execute("""
                SELECT timestamp, decision, reason, krw_balance
                FROM trades 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            
            recent_trades = cursor.fetchall()
            
            print(f"   {'시간':<25} {'결정':<6} {'KRW잔액':<12} {'이유'}")
            print("   " + "-" * 70)
            
            for trade in recent_trades:
                timestamp, decision, reason, krw_balance = trade
                reason_short = (reason[:35] + "...") if reason and len(reason) > 35 else (reason or "")
                print(f"   {timestamp:<25} {decision:<6} {krw_balance:>12,.0f} {reason_short}")
            
        else:
            print("❌ 삭제 작업이 취소되었습니다.")
        
        conn.close()
        
        print(f"\n🎉 작업 완료!")
        print(f"📊 대시보드를 새로고침하면 변경사항이 반영됩니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def show_all_manual_records():
    """모든 수동 관련 기록 조회"""
    try:
        conn = sqlite3.connect('bitcoin_trades.db')
        
        print("\n🔍 모든 수동 관련 기록 조회:")
        
        # 더 넓은 범위로 검색
        df = pd.read_sql_query("""
            SELECT id, timestamp, decision, reason, krw_balance,
                   krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change
            FROM trades 
            WHERE reason LIKE '%Manual%' 
               OR reason LIKE '%수동%'
               OR reason LIKE '%누락%'
               OR reason LIKE '%복구%'
               OR ABS(krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp)) = 500000
            ORDER BY timestamp DESC
        """, conn)
        
        if len(df) > 0:
            print(f"   발견된 의심 기록: {len(df)}개")
            print(df.to_string(index=False))
        else:
            print("   관련 기록이 없습니다.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 조회 오류: {e}")

if __name__ == "__main__":
    # 먼저 모든 관련 기록 확인
    show_all_manual_records()
    
    # 삭제 실행
    delete_manual_deposit_records()