# -*- coding:utf-8 -*-
import sqlite3
import os
from loguru import logger

class DatabaseManager:
    def __init__(self, db_path=None):
        """
        db_path가 제공되지 않으면 환경 변수 ENV와 실행 경로를 기반으로 자동 결정합니다.
        예: prod_consensus.db, dev_consensus.db
        """
        if db_path is None:
            # 1. 환경 변수 확인
            env = os.getenv("ENV", "dev").lower()
            # 2. 경로 기반 자동 감지 (상위 경로에 dev가 포함되어 있는지)
            current_path = os.getcwd().lower()
            if "dev" in current_path and env != "production":
                env = "dev"
            
            # 3. Docker 여부에 따른 기본 경로 설정
            is_docker = os.path.exists("/app")
            base_dir = "/app/db" if is_docker else "./db"
            
            prefix = "prod" if env in ["production", "prod"] else "dev"
            db_path = os.path.join(base_dir, f"{prefix}_consensus.db")

        self.db_path = db_path
        logger.debug(f"Database initialized at: {self.db_path}")
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        # WAL 모드 활성화: 쓰기 중에도 읽기(SELECT)가 가능해져서 'database is locked' 현상을 대폭 줄여줍니다.
        conn.execute('PRAGMA journal_mode=WAL;')
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS report_history (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    REPORT_IDX TEXT UNIQUE,
                    TITLE TEXT,
                    URL TEXT UNIQUE,
                    PDF_URL TEXT,
                    SOURCE TEXT,
                    BROKER TEXT,
                    REG_DT TEXT,
                    SENT_YN TEXT DEFAULT 'N',
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 인덱스 추가 (조회 속도 향상)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_report_reg_dt ON report_history(REG_DT)")
            
            cursor = conn.execute("PRAGMA table_info(report_history)")
            actual_cols = {row[1].upper(): row[1] for row in cursor.fetchall()}
            
            if 'REPORT_IDX' not in actual_cols:
                conn.execute("ALTER TABLE report_history ADD COLUMN REPORT_IDX TEXT")
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_report_idx ON report_history(REPORT_IDX)")

            conn.commit()

    def insert_report(self, title, url, source, broker, report_idx=None, reg_dt=None, pdf_url=None, sent_yn='N'):
        try:
            with self._get_connection() as conn:
                # 1. IDX 기반 중복 체크
                if report_idx:
                    cursor = conn.execute("SELECT 1 FROM report_history WHERE REPORT_IDX = ?", (report_idx,))
                    if cursor.fetchone():
                        return False

                # 2. 데이터 삽입
                conn.execute('''
                    INSERT INTO report_history (REPORT_IDX, TITLE, URL, PDF_URL, SOURCE, BROKER, REG_DT, SENT_YN) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (report_idx, title, url, pdf_url, source, broker, reg_dt, sent_yn))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"DB Insert Error: {e}")
            return False

    def get_unsent_reports(self):
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM report_history WHERE SENT_YN = 'N' ORDER BY ID ASC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"DB Select Error (Unsent): {e}")
            return []

    def update_sent_status(self, report_ids):
        if not report_ids: return
        try:
            with self._get_connection() as conn:
                placeholders = ','.join(['?'] * len(report_ids))
                conn.execute(f"UPDATE report_history SET SENT_YN = 'Y' WHERE ID IN ({placeholders})", report_ids)
                conn.commit()
        except Exception as e:
            logger.error(f"DB Update Error: {e}")
