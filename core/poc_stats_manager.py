"""
POC 使用统计管理器 - 记录 POC 使用次数和发现漏洞次数
独立模块，通过钩子方式集成，不修改现有核心逻辑
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class POCStatsManager:
    """POC 使用统计管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化统计管理器
        
        参数:
            db_path: 数据库文件路径，默认为当前目录下的 poc_stats.db
        """
        if db_path is None:
            db_path = "poc_stats.db"
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # POC 使用统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poc_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poc_id TEXT NOT NULL,
                poc_path TEXT,
                use_count INTEGER DEFAULT 0,
                vuln_count INTEGER DEFAULT 0,
                last_used_at TEXT,
                first_used_at TEXT,
                UNIQUE(poc_id)
            )
        ''')
        
        # POC 使用历史记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poc_usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poc_id TEXT NOT NULL,
                scan_id INTEGER,
                target_count INTEGER DEFAULT 0,
                vuln_found INTEGER DEFAULT 0,
                used_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_usage(self, poc_id: str, poc_path: str = None, 
                     vuln_found: int = 0, target_count: int = 0,
                     scan_id: int = None):
        """
        记录 POC 使用情况
        
        参数:
            poc_id: POC 的唯一标识
            poc_path: POC 文件路径
            vuln_found: 本次发现的漏洞数量
            target_count: 本次扫描的目标数量
            scan_id: 关联的扫描记录 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            # 更新或插入使用统计
            cursor.execute('''
                INSERT INTO poc_usage (poc_id, poc_path, use_count, vuln_count, last_used_at, first_used_at)
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(poc_id) DO UPDATE SET
                    use_count = use_count + 1,
                    vuln_count = vuln_count + ?,
                    last_used_at = ?,
                    poc_path = COALESCE(?, poc_path)
            ''', (poc_id, poc_path, vuln_found, now, now, vuln_found, now, poc_path))
            
            # 记录使用历史
            cursor.execute('''
                INSERT INTO poc_usage_history (poc_id, scan_id, target_count, vuln_found, used_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (poc_id, scan_id, target_count, vuln_found, now))
            
            conn.commit()
        except Exception as e:
            print(f"记录 POC 使用统计失败: {e}")
        finally:
            conn.close()
    
    def record_batch_usage(self, poc_stats: List[Dict]):
        """
        批量记录 POC 使用情况
        
        参数:
            poc_stats: POC 统计列表，每项包含 {'poc_id', 'poc_path', 'vuln_found', 'target_count', 'scan_id'}
        """
        for stat in poc_stats:
            self.record_usage(
                poc_id=stat.get('poc_id', ''),
                poc_path=stat.get('poc_path'),
                vuln_found=stat.get('vuln_found', 0),
                target_count=stat.get('target_count', 0),
                scan_id=stat.get('scan_id')
            )
    
    def get_poc_stats(self, poc_id: str) -> Optional[Dict]:
        """
        获取单个 POC 的使用统计
        
        参数:
            poc_id: POC 的唯一标识
        
        返回:
            统计信息字典，不存在则返回 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT poc_id, poc_path, use_count, vuln_count, last_used_at, first_used_at
            FROM poc_usage
            WHERE poc_id = ?
        ''', (poc_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'poc_id': row[0],
                'poc_path': row[1],
                'use_count': row[2],
                'vuln_count': row[3],
                'last_used_at': row[4],
                'first_used_at': row[5],
            }
        return None
    
    def get_top_used_pocs(self, limit: int = 20) -> List[Dict]:
        """
        获取使用次数最多的 POC
        
        参数:
            limit: 返回数量限制
        
        返回:
            POC 统计列表，按使用次数降序排列
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT poc_id, poc_path, use_count, vuln_count, last_used_at
            FROM poc_usage
            ORDER BY use_count DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'poc_id': row[0],
            'poc_path': row[1],
            'use_count': row[2],
            'vuln_count': row[3],
            'last_used_at': row[4],
        } for row in rows]
    
    def get_most_effective_pocs(self, limit: int = 20) -> List[Dict]:
        """
        获取发现漏洞最多的 POC（最有效的）
        
        参数:
            limit: 返回数量限制
        
        返回:
            POC 统计列表，按发现漏洞数降序排列
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT poc_id, poc_path, use_count, vuln_count, last_used_at
            FROM poc_usage
            WHERE vuln_count > 0
            ORDER BY vuln_count DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'poc_id': row[0],
            'poc_path': row[1],
            'use_count': row[2],
            'vuln_count': row[3],
            'last_used_at': row[4],
            'effectiveness': round(row[3] / max(row[2], 1) * 100, 1),  # 有效率百分比
        } for row in rows]
    
    def get_recent_used_pocs(self, limit: int = 20) -> List[Dict]:
        """
        获取最近使用的 POC
        
        参数:
            limit: 返回数量限制
        
        返回:
            POC 统计列表，按最后使用时间降序排列
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT poc_id, poc_path, use_count, vuln_count, last_used_at
            FROM poc_usage
            ORDER BY last_used_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'poc_id': row[0],
            'poc_path': row[1],
            'use_count': row[2],
            'vuln_count': row[3],
            'last_used_at': row[4],
        } for row in rows]
    
    def get_all_stats(self) -> Dict:
        """
        获取 POC 使用统计概览
        
        返回:
            统计概览字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总计
        cursor.execute('SELECT COUNT(*), SUM(use_count), SUM(vuln_count) FROM poc_usage')
        row = cursor.fetchone()
        
        total_pocs = row[0] or 0
        total_uses = row[1] or 0
        total_vulns = row[2] or 0
        
        # 从未使用的 POC 数量（这个需要与 POC 库对比）
        # 这里只返回已使用的统计
        
        conn.close()
        
        return {
            'total_pocs_used': total_pocs,
            'total_scan_uses': total_uses,
            'total_vulns_found': total_vulns,
            'avg_vulns_per_use': round(total_vulns / max(total_uses, 1), 2),
        }
    
    def get_usage_history(self, poc_id: str, limit: int = 50) -> List[Dict]:
        """
        获取 POC 的使用历史记录
        
        参数:
            poc_id: POC 的唯一标识
            limit: 返回数量限制
        
        返回:
            使用历史列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT scan_id, target_count, vuln_found, used_at
            FROM poc_usage_history
            WHERE poc_id = ?
            ORDER BY used_at DESC
            LIMIT ?
        ''', (poc_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'scan_id': row[0],
            'target_count': row[1],
            'vuln_found': row[2],
            'used_at': row[3],
        } for row in rows]


# 单例模式
_stats_manager_instance = None

def get_poc_stats_manager(db_path: str = None) -> POCStatsManager:
    """
    获取 POC 统计管理器单例
    
    参数:
        db_path: 数据库文件路径（首次调用时生效）
    """
    global _stats_manager_instance
    
    if _stats_manager_instance is None:
        _stats_manager_instance = POCStatsManager(db_path)
    
    return _stats_manager_instance
