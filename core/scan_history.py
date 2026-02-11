"""
扫描历史记录管理 - 使用 SQLite 存储
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path


class ScanHistory:
    """
    扫描历史记录管理器
    使用 SQLite 数据库存储
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认存储在程序目录下
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scan_history.db")
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 扫描记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    target_count INTEGER,
                    poc_count INTEGER,
                    vuln_count INTEGER,
                    duration_seconds REAL,
                    status TEXT DEFAULT '扫描完成',
                    targets TEXT,
                    pocs TEXT,
                    config TEXT
                )
            ''')

            # 检查是否需要添加 status 字段（兼容旧数据库）
            cursor.execute("PRAGMA table_info(scan_records)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'status' not in columns:
                cursor.execute("ALTER TABLE scan_records ADD COLUMN status TEXT DEFAULT '扫描完成'")

            # 检查是否需要添加 template_path 字段（兼容旧数据库）
            cursor.execute("PRAGMA table_info(vuln_results)")
            v_columns = [col[1] for col in cursor.fetchall()]
            if 'template_path' not in v_columns:
                cursor.execute("ALTER TABLE vuln_results ADD COLUMN template_path TEXT")

            # 漏洞结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vuln_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    template_id TEXT,
                    template_path TEXT,
                    matched_at TEXT,
                    severity TEXT,
                    timestamp TEXT,
                    raw_json TEXT,
                    FOREIGN KEY (scan_id) REFERENCES scan_records(id)
                )
            ''')

            conn.commit()
    
    def add_scan_record(self, target_count: int, poc_count: int, vuln_count: int,
                        duration: float, targets: list, pocs: list, config: dict,
                        status: str = "扫描完成") -> int:
        """添加扫描记录，返回记录ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO scan_records
                (target_count, poc_count, vuln_count, duration_seconds, status, targets, pocs, config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (target_count, poc_count, vuln_count, duration, status,
                  json.dumps(targets[:100], ensure_ascii=False),  # 只保存前100个
                  json.dumps(pocs[:50], ensure_ascii=False),      # 只保存前50个
                  json.dumps(config, ensure_ascii=False)))

            scan_id = cursor.lastrowid
            conn.commit()
            return scan_id
    
    def add_vuln_result(self, scan_id: int, result: dict):
        """添加漏洞结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO vuln_results
                (scan_id, template_id, template_path, matched_at, severity, timestamp, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (scan_id,
                  result.get('template-id', ''),
                  result.get('template-path', ''),
                  result.get('matched-at', ''),
                  result.get('info', {}).get('severity', 'unknown'),
                  result.get('timestamp', ''),
                  json.dumps(result, ensure_ascii=False)))

            conn.commit()
    
    def get_recent_scans(self, limit: int = 20) -> list:
        """获取最近的扫描记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM scan_records
                ORDER BY scan_time DESC
                LIMIT ?
            ''', (limit,))

            results = [dict(row) for row in cursor.fetchall()]
            return results
    
    def get_scan_record(self, scan_id: int) -> dict:
        """获取单条扫描记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM scan_records
                WHERE id = ?
            ''', (scan_id,))

            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_scan_vulns(self, scan_id: int) -> list:
        """获取扫描的漏洞结果"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM vuln_results
                WHERE scan_id = ?
                ORDER BY id
            ''', (scan_id,))

            results = [dict(row) for row in cursor.fetchall()]
            return results
    
    def get_statistics(self) -> dict:
        """获取统计数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 总扫描次数
            cursor.execute('SELECT COUNT(*) FROM scan_records')
            total_scans = cursor.fetchone()[0]

            # 总发现漏洞数
            cursor.execute('SELECT COUNT(*) FROM vuln_results')
            total_vulns = cursor.fetchone()[0]

            # 漏洞严重程度分布
            cursor.execute('''
                SELECT severity, COUNT(*) as count
                FROM vuln_results
                GROUP BY severity
            ''')
            severity_dist = {row[0]: row[1] for row in cursor.fetchall()}

            # 最近7天趋势
            cursor.execute('''
                SELECT DATE(scan_time) as date,
                       SUM(vuln_count) as vulns,
                       COUNT(*) as scans
                FROM scan_records
                WHERE scan_time >= DATE('now', '-7 days')
                GROUP BY DATE(scan_time)
                ORDER BY date
            ''')
            trend_7days = [{'date': row[0], 'vulns': row[1], 'scans': row[2]} for row in cursor.fetchall()]

            # TOP 5 漏洞模板
            cursor.execute('''
                SELECT template_id, COUNT(*) as count
                FROM vuln_results
                GROUP BY template_id
                ORDER BY count DESC
                LIMIT 5
            ''')
            top_templates = [{'template': row[0], 'count': row[1]} for row in cursor.fetchall()]

            return {
                'total_scans': total_scans,
                'total_vulns': total_vulns,
                'severity_distribution': severity_dist,
                'trend_7days': trend_7days,
                'top_templates': top_templates
            }
    
    def delete_scan(self, scan_id: int):
        """删除扫描记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM vuln_results WHERE scan_id = ?', (scan_id,))
            cursor.execute('DELETE FROM scan_records WHERE id = ?', (scan_id,))

            conn.commit()
    
    def get_all_scans(self, page: int = 1, page_size: int = 50) -> dict:
        """分页获取所有扫描记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 获取总记录数
            cursor.execute('SELECT COUNT(*) FROM scan_records')
            total = cursor.fetchone()[0]

            # 分页查询
            offset = (page - 1) * page_size
            cursor.execute('''
                SELECT * FROM scan_records
                ORDER BY scan_time DESC
                LIMIT ? OFFSET ?
            ''', (page_size, offset))

            records = [dict(row) for row in cursor.fetchall()]

            return {
                'total': total,
                'page': page,
                'page_size': page_size,
                'records': records
            }
    
    def clear_history(self):
        """清空所有历史记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM vuln_results')
            cursor.execute('DELETE FROM scan_records')

            conn.commit()


# 全局单例
_history_instance = None

def get_scan_history() -> ScanHistory:
    """获取历史管理器单例"""
    global _history_instance
    if _history_instance is None:
        _history_instance = ScanHistory()
    return _history_instance
