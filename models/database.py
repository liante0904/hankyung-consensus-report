# -*- coding:utf-8 -*-
import sqlite3
import os
from loguru import logger

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            # 뉴스용 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS news_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # 레포트용 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS report_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    url TEXT UNIQUE,
                    source TEXT,
                    broker TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def insert_article(self, title, url, source):
        try:
            with self._get_connection() as conn:
                conn.execute('INSERT INTO news_history (title, url, source) VALUES (?, ?, ?)', (title, url, source))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"DB Insert Error (News): {e}")
            return False

    def insert_report(self, title, url, source, broker):
        try:
            with self._get_connection() as conn:
                conn.execute('INSERT INTO report_history (title, url, source, broker) VALUES (?, ?, ?, ?)', (title, url, source, broker))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"DB Insert Error (Report): {e}")
            return False
