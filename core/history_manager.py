"""
历史记录管理 - 用于 FOFA 搜索和 AI 生成记录
使用 SQLite 存储
"""
import sqlite3
import json
import os
from datetime import datetime


class HistoryManager:
    """通用历史记录管理器"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.db")
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # FOFA 搜索历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fofa_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    result_count INTEGER DEFAULT 0,
                    search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    results TEXT
                )
            ''')

            # AI 生成历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    output_text TEXT,
                    model_name TEXT,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()

    # ========== FOFA 历史 ==========
    def add_fofa_history(self, query: str, result_count: int = 0, results: list = None) -> int:
        """添加 FOFA 搜索历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 检查是否已存在相同查询，如果存在则更新
            cursor.execute('SELECT id FROM fofa_history WHERE query = ?', (query,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute('''
                    UPDATE fofa_history
                    SET result_count = ?, search_time = CURRENT_TIMESTAMP, results = ?
                    WHERE id = ?
                ''', (result_count, json.dumps(results if results else [], ensure_ascii=False), existing[0]))
                record_id = existing[0]
            else:
                cursor.execute('''
                    INSERT INTO fofa_history (query, result_count, results)
                    VALUES (?, ?, ?)
                ''', (query, result_count, json.dumps(results if results else [], ensure_ascii=False)))
                record_id = cursor.lastrowid

            conn.commit()
            return record_id

    def get_fofa_history(self, limit: int = 20) -> list:
        """获取 FOFA 搜索历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM fofa_history
                ORDER BY search_time DESC
                LIMIT ?
            ''', (limit,))

            results = [dict(row) for row in cursor.fetchall()]
            return results

    def get_fofa_results(self, history_id: int) -> list:
        """获取 FOFA 历史记录的结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT results FROM fofa_history WHERE id = ?', (history_id,))
            row = cursor.fetchone()

            if row and row[0]:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return []
            return []

    def delete_fofa_history(self, history_id: int):
        """删除 FOFA 历史记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM fofa_history WHERE id = ?', (history_id,))
            conn.commit()

    def clear_fofa_history(self):
        """清空 FOFA 历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM fofa_history')
            conn.commit()

    # ========== AI 历史 ==========
    def add_ai_history(self, task_type: str, input_text: str, output_text: str, model_name: str = "") -> int:
        """添加 AI 生成历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO ai_history (task_type, input_text, output_text, model_name)
                VALUES (?, ?, ?, ?)
            ''', (task_type, input_text, output_text, model_name))

            record_id = cursor.lastrowid
            conn.commit()
            return record_id

    def get_ai_history(self, task_type: str = None, limit: int = 20) -> list:
        """获取 AI 生成历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if task_type:
                cursor.execute('''
                    SELECT * FROM ai_history
                    WHERE task_type = ?
                    ORDER BY create_time DESC
                    LIMIT ?
                ''', (task_type, limit))
            else:
                cursor.execute('''
                    SELECT * FROM ai_history
                    ORDER BY create_time DESC
                    LIMIT ?
                ''', (limit,))

            results = [dict(row) for row in cursor.fetchall()]
            return results

    def delete_ai_history(self, history_id: int):
        """删除 AI 历史记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ai_history WHERE id = ?', (history_id,))
            conn.commit()

    def clear_ai_history(self):
        """清空 AI 历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ai_history')
            conn.commit()

    # ========== 扫描历史 ==========
    def init_scan_history(self):
        """初始化扫描历史表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_count INTEGER,
                    poc_count INTEGER,
                    duration REAL,
                    vuln_count INTEGER,
                    status TEXT,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    results TEXT
                )
            ''')
            conn.commit()

    def add_scan_history(self, target_count: int, poc_count: int, duration: float,
                         vuln_count: int, status: str, results: list = None) -> int:
        """添加扫描历史记录"""
        # 确保表存在
        self.init_scan_history()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO scan_history (target_count, poc_count, duration, vuln_count, status, results)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (target_count, poc_count, duration, vuln_count, status,
                  json.dumps(results if results else [], ensure_ascii=False)))

            record_id = cursor.lastrowid
            conn.commit()
            return record_id

    def get_scan_history(self, limit: int = 50) -> list:
        """获取扫描历史"""
        # 确保表存在
        self.init_scan_history()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM scan_history
                ORDER BY scan_time DESC
                LIMIT ?
            ''', (limit,))

            results = [dict(row) for row in cursor.fetchall()]
            return results

    def get_scan_results(self, history_id: int) -> list:
        """获取扫描历史的具体结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT results FROM scan_history WHERE id = ?', (history_id,))
            row = cursor.fetchone()

            if row and row[0]:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return []
            return []

    def clear_scan_history(self):
        """清空扫描历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('DELETE FROM scan_history')
                conn.commit()
            except sqlite3.Error:
                pass


# 全局单例
_history_instance = None

def get_history_manager() -> HistoryManager:
    """获取历史管理器单例"""
    global _history_instance
    if _history_instance is None:
        _history_instance = HistoryManager()
    return _history_instance
