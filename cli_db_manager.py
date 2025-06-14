#!/usr/bin/env python3
"""
Bitcoin Trading Database CLI Manager
AWS EC2에서 CLI로 데이터베이스를 관리하는 도구
"""

import sqlite3
import pandas as pd
from datetime import datetime
import argparse
import sys
import json
from tabulate import tabulate

class CLIDBManager:
    def __init__(self, db_path='bitcoin_trades.db'):
        self.db_path = db_path
        self.ensure_columns()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def ensure_columns(self):
        """필요한 컬럼들이 존재하는지 확인하고 없으면 추가"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 기존 컬럼 확인
        c.execute("PRAGMA table_info(trades)")
        existing_columns = [col[1] for col in c.fetchall()]
        
        # 필요한 컬럼들 추가
        new_columns = [
            ('transaction_type', 'TEXT DEFAULT "trade"'),
            ('manual_entry', 'INTEGER DEFAULT 0'),
            ('notes', 'TEXT')
        ]
        
        for col_name, col_def in new_columns:
            if col_name not in existing_columns:
                try:
                    c.execute(f'ALTER TABLE trades ADD COLUMN {col_name} {col_def}')
                    print(f"✅ {col_name} 컬럼 추가됨")
                except sqlite3.OperationalError:
                    pass  # 이미 존재하면 무시
        
        conn.commit()
        conn.close()
    
    def view_trades(self, limit=20, transaction_type=None, trade_id=None):
        """거래 내역 조회"""
        conn = self.get_connection()
        
        if trade_id:
            # 특정 ID 조회
            query = "SELECT * FROM trades WHERE id = ?"
            params = [trade_id]
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                print(f"❌ ID {trade_id}에 해당하는 거래를 찾을 수 없습니다.")
                conn.close()
                return
            
            # 상세 정보 출력
            trade = df.iloc[0]
            print(f"\n🔍 거래 상세 정보 (ID: {trade_id})")
            print("=" * 60)
            print(f"시간: {trade['timestamp']}")
            print(f"거래 유형: {trade.get('transaction_type', 'trade')}")
            print(f"결정: {trade['decision']}")
            print(f"비율: {trade['percentage']}%")
            print(f"BTC 잔고: {trade['btc_balance']:.8f}")
            print(f"KRW 잔고: {trade['krw_balance']:,.0f}원")
            print(f"BTC 평균 매수가: {trade['btc_avg_buy_price']:,.0f}원")
            print(f"BTC 현재가: {trade['btc_krw_price']:,.0f}원")
            print(f"이유: {trade['reason']}")
            if trade.get('notes'):
                print(f"메모: {trade['notes']}")
            if trade.get('reflection'):
                print(f"반성: {trade['reflection']}")
            print(f"수동 입력: {'예' if trade.get('manual_entry') else '아니오'}")
            
        else:
            # 일반 조회
            query = "SELECT id, timestamp, transaction_type, decision, percentage, btc_balance, krw_balance, reason FROM trades"
            params = []
            
            if transaction_type:
                query += " WHERE transaction_type = ?"
                params.append(transaction_type)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                print("📭 거래 내역이 없습니다.")
                conn.close()
                return
            
            # timestamp 포맷팅
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%m-%d %H:%M')
            
            # 잔고 포맷팅
            df['btc_balance'] = df['btc_balance'].apply(lambda x: f"{x:.6f}")
            df['krw_balance'] = df['krw_balance'].apply(lambda x: f"{x:,.0f}")
            
            # 테이블 출력
            print(f"\n📊 거래 내역 (최근 {len(df)}건)")
            print("=" * 100)
            print(tabulate(df, headers=df.columns, tablefmt='grid', showindex=False))
        
        conn.close()
    
    def add_deposit(self, amount, description="Manual deposit"):
        """입금 추가"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 최신 거래 정보 가져오기
        c.execute("SELECT btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price FROM trades ORDER BY timestamp DESC LIMIT 1")
        latest = c.fetchone()
        
        if not latest:
            print("❌ 기존 거래 내역이 없습니다.")
            conn.close()
            return False
        
        timestamp = datetime.now().isoformat()
        new_krw_balance = latest[1] + amount
        
        c.execute("""INSERT INTO trades 
                     (timestamp, decision, percentage, reason, btc_balance, krw_balance, 
                      btc_avg_buy_price, btc_krw_price, transaction_type, manual_entry, notes) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (timestamp, 'hold', 0, f'Manual deposit: {description}', 
                   latest[0], new_krw_balance, latest[2], latest[3], 
                   'deposit', 1, description))
        
        conn.commit()
        conn.close()
        print(f"✅ {amount:,}원 입금 내역이 추가되었습니다.")
        return True
    
    def add_withdrawal(self, amount, description="Manual withdrawal"):
        """출금 추가"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 최신 거래 정보 가져오기
        c.execute("SELECT btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price FROM trades ORDER BY timestamp DESC LIMIT 1")
        latest = c.fetchone()
        
        if not latest:
            print("❌ 기존 거래 내역이 없습니다.")
            conn.close()
            return False
        
        if latest[1] < amount:
            print(f"❌ 잔고 부족: 현재 {latest[1]:,}원, 출금 요청 {amount:,}원")
            conn.close()
            return False
        
        timestamp = datetime.now().isoformat()
        new_krw_balance = latest[1] - amount
        
        c.execute("""INSERT INTO trades 
                     (timestamp, decision, percentage, reason, btc_balance, krw_balance, 
                      btc_avg_buy_price, btc_krw_price, transaction_type, manual_entry, notes) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (timestamp, 'hold', 0, f'Manual withdrawal: {description}', 
                   latest[0], new_krw_balance, latest[2], latest[3], 
                   'withdrawal', 1, description))
        
        conn.commit()
        conn.close()
        print(f"✅ {amount:,}원 출금 내역이 추가되었습니다.")
        return True
    
    def delete_trade(self, trade_id, force=False):
        """거래 삭제"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 삭제할 거래 확인
        c.execute("SELECT timestamp, transaction_type, reason FROM trades WHERE id = ?", (trade_id,))
        trade = c.fetchone()
        
        if not trade:
            print(f"❌ ID {trade_id}에 해당하는 거래를 찾을 수 없습니다.")
            conn.close()
            return False
        
        print(f"삭제할 거래: ID {trade_id} | {trade[0]} | {trade[1]} | {trade[2]}")
        
        if not force:
            confirm = input("정말 삭제하시겠습니까? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ 삭제가 취소되었습니다.")
                conn.close()
                return False
        
        c.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        conn.commit()
        conn.close()
        print(f"✅ ID {trade_id} 거래가 삭제되었습니다.")
        return True
    
    def update_type(self, trade_id, new_type):
        """거래 유형 수정"""
        valid_types = ['trade', 'deposit', 'withdrawal', 'fee', 'other']
        if new_type not in valid_types:
            print(f"❌ 유효하지 않은 거래 유형: {new_type}")
            print(f"사용 가능한 유형: {', '.join(valid_types)}")
            return False
        
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute("UPDATE trades SET transaction_type = ? WHERE id = ?", (new_type, trade_id))
        
        if c.rowcount > 0:
            conn.commit()
            print(f"✅ ID {trade_id}의 거래 유형이 '{new_type}'으로 변경되었습니다.")
            result = True
        else:
            print(f"❌ ID {trade_id}에 해당하는 거래를 찾을 수 없습니다.")
            result = False
        
        conn.close()
        return result
    
    def summary(self):
        """요약 정보"""
        conn = self.get_connection()
        
        # 전체 통계
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM trades")
        total_trades = c.fetchone()[0]
        
        # 거래 유형별 통계
        c.execute("""
            SELECT transaction_type, COUNT(*) as count 
            FROM trades 
            GROUP BY transaction_type 
            ORDER BY count DESC
        """)
        type_stats = c.fetchall()
        
        # 최신 잔고
        c.execute("SELECT btc_balance, krw_balance, btc_krw_price FROM trades ORDER BY timestamp DESC LIMIT 1")
        latest = c.fetchone()
        
        conn.close()
        
        print(f"\n📈 거래 요약")
        print("=" * 50)
        print(f"총 거래 수: {total_trades}건")
        
        if latest:
            total_asset = latest[0] * latest[2] + latest[1]
            print(f"현재 BTC: {latest[0]:.6f}")
            print(f"현재 KRW: {latest[1]:,.0f}원")
            print(f"총 자산: {total_asset:,.0f}원")
        
        print(f"\n거래 유형별 통계:")
        for trans_type, count in type_stats:
            print(f"  {trans_type}: {count}건")
    
    def search(self, keyword):
        """키워드로 검색"""
        conn = self.get_connection()
        
        query = """
            SELECT id, timestamp, transaction_type, decision, reason 
            FROM trades 
            WHERE reason LIKE ? OR notes LIKE ?
            ORDER BY timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn, params=[f"%{keyword}%", f"%{keyword}%"])
        conn.close()
        
        if df.empty:
            print(f"📭 '{keyword}' 검색 결과가 없습니다.")
            return
        
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%m-%d %H:%M')
        
        print(f"\n🔍 '{keyword}' 검색 결과 ({len(df)}건)")
        print("=" * 80)
        print(tabulate(df, headers=df.columns, tablefmt='grid', showindex=False))
    
    def backup(self, backup_path=None):
        """데이터베이스 백업"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_bitcoin_trades_{timestamp}.db"
        
        import shutil
        try:
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ 데이터베이스가 {backup_path}로 백업되었습니다.")
            return True
        except Exception as e:
            print(f"❌ 백업 실패: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Bitcoin Trading Database CLI Manager')
    parser.add_argument('--db', default='bitcoin_trades.db', help='Database file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # view 명령
    view_parser = subparsers.add_parser('view', help='View trades')
    view_parser.add_argument('--limit', type=int, default=20, help='Number of records to show')
    view_parser.add_argument('--type', choices=['trade', 'deposit', 'withdrawal', 'fee', 'other'], help='Filter by transaction type')
    view_parser.add_argument('--id', type=int, help='View specific trade by ID')
    
    # deposit 명령
    deposit_parser = subparsers.add_parser('deposit', help='Add manual deposit')
    deposit_parser.add_argument('amount', type=int, help='Deposit amount')
    deposit_parser.add_argument('--desc', default='Manual deposit', help='Description')
    
    # withdraw 명령
    withdraw_parser = subparsers.add_parser('withdraw', help='Add manual withdrawal')
    withdraw_parser.add_argument('amount', type=int, help='Withdrawal amount')
    withdraw_parser.add_argument('--desc', default='Manual withdrawal', help='Description')
    
    # delete 명령
    delete_parser = subparsers.add_parser('delete', help='Delete trade')
    delete_parser.add_argument('id', type=int, help='Trade ID to delete')
    delete_parser.add_argument('--force', action='store_true', help='Force delete without confirmation')
    
    # update 명령
    update_parser = subparsers.add_parser('update', help='Update transaction type')
    update_parser.add_argument('id', type=int, help='Trade ID to update')
    update_parser.add_argument('type', choices=['trade', 'deposit', 'withdrawal', 'fee', 'other'], help='New transaction type')
    
    # search 명령
    search_parser = subparsers.add_parser('search', help='Search trades')
    search_parser.add_argument('keyword', help='Search keyword')
    
    # summary 명령
    subparsers.add_parser('summary', help='Show summary')
    
    # backup 명령
    backup_parser = subparsers.add_parser('backup', help='Backup database')
    backup_parser.add_argument('--path', help='Backup file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 데이터베이스 매니저 생성
    try:
        db_manager = CLIDBManager(args.db)
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return
    
    # 명령 실행
    try:
        if args.command == 'view':
            db_manager.view_trades(args.limit, args.type, args.id)
        
        elif args.command == 'deposit':
            db_manager.add_deposit(args.amount, args.desc)
        
        elif args.command == 'withdraw':
            db_manager.add_withdrawal(args.amount, args.desc)
        
        elif args.command == 'delete':
            db_manager.delete_trade(args.id, args.force)
        
        elif args.command == 'update':
            db_manager.update_type(args.id, args.type)
        
        elif args.command == 'search':
            db_manager.search(args.keyword)
        
        elif args.command == 'summary':
            db_manager.summary()
        
        elif args.command == 'backup':
            db_manager.backup(args.path)
        
    except Exception as e:
        print(f"❌ 명령 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()