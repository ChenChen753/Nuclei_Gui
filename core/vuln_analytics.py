"""
漏洞趋势分析模块
提供漏洞数据统计、趋势分析功能
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import get_logger

logger = get_logger('vuln_analytics')


@dataclass
class VulnRecord:
    """漏洞记录"""
    id: str
    template_id: str
    name: str
    severity: str
    host: str
    matched_at: str
    timestamp: datetime
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_scan_result(cls, result: Dict) -> 'VulnRecord':
        """从扫描结果创建漏洞记录"""
        info = result.get('info', {})
        return cls(
            id=result.get('template-id', '') + '_' + result.get('matched-at', ''),
            template_id=result.get('template-id', ''),
            name=info.get('name', result.get('template-id', '')),
            severity=info.get('severity', 'unknown'),
            host=result.get('host', ''),
            matched_at=result.get('matched-at', ''),
            timestamp=datetime.now(),
            tags=info.get('tags', [])
        )


class VulnAnalytics:
    """漏洞分析引擎"""
    
    SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info', 'unknown']
    SEVERITY_COLORS = {
        'critical': '#dc2626',
        'high': '#ea580c',
        'medium': '#ca8a04',
        'low': '#16a34a',
        'info': '#2563eb',
        'unknown': '#6b7280'
    }
    
    def __init__(self, data_dir: str = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            self.data_dir = Path(app_data) / 'NucleiGUI' / 'analytics'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._vuln_records: List[VulnRecord] = []
        self._load_history()
    
    def _get_history_file(self) -> Path:
        """获取历史数据文件路径"""
        return self.data_dir / 'vuln_history.json'
    
    def _load_history(self):
        """加载历史漏洞数据"""
        history_file = self._get_history_file()
        if not history_file.exists():
            return
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for record in data.get('records', []):
                self._vuln_records.append(VulnRecord(
                    id=record['id'],
                    template_id=record['template_id'],
                    name=record['name'],
                    severity=record['severity'],
                    host=record['host'],
                    matched_at=record['matched_at'],
                    timestamp=datetime.fromisoformat(record['timestamp']),
                    tags=record.get('tags', [])
                ))
            logger.info(f'Loaded {len(self._vuln_records)} vuln records')
        except Exception as e:
            logger.error(f'Load history failed: {e}')
    
    def _save_history(self):
        """保存历史漏洞数据"""
        try:
            data = {
                'records': [
                    {
                        'id': r.id,
                        'template_id': r.template_id,
                        'name': r.name,
                        'severity': r.severity,
                        'host': r.host,
                        'matched_at': r.matched_at,
                        'timestamp': r.timestamp.isoformat(),
                        'tags': r.tags
                    }
                    for r in self._vuln_records
                ],
                'updated_at': datetime.now().isoformat()
            }
            with open(self._get_history_file(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f'Save history failed: {e}')
    
    def add_scan_results(self, results: List[Dict]):
        """添加扫描结果到历史记录"""
        for result in results:
            record = VulnRecord.from_scan_result(result)
            self._vuln_records.append(record)
        self._save_history()
        logger.info(f'Added {len(results)} vuln records')
    
    def get_severity_distribution(self, days: int = None) -> Dict[str, int]:
        """获取漏洞严重程度分布"""
        records = self._filter_by_days(days)
        distribution = defaultdict(int)
        for record in records:
            distribution[record.severity] += 1
        for severity in self.SEVERITY_ORDER:
            if severity not in distribution:
                distribution[severity] = 0
        return dict(distribution)
    
    def get_trend_data(self, days: int = 30) -> Dict:
        """获取漏洞趋势数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_groups = defaultdict(lambda: defaultdict(int))
        
        for record in self._vuln_records:
            if record.timestamp >= start_date:
                date_key = record.timestamp.strftime('%Y-%m-%d')
                date_groups[date_key][record.severity] += 1
                date_groups[date_key]['total'] += 1
        
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        trend_data = {'dates': dates, 'series': {}}
        for severity in self.SEVERITY_ORDER + ['total']:
            trend_data['series'][severity] = [date_groups[d][severity] for d in dates]
        return trend_data
    
    def get_top_vulnerabilities(self, limit: int = 10, days: int = None) -> List[Dict]:
        """获取出现次数最多的漏洞类型"""
        records = self._filter_by_days(days)
        vuln_counts = defaultdict(lambda: {'count': 0, 'severity': '', 'name': ''})
        
        for record in records:
            vuln_counts[record.template_id]['count'] += 1
            vuln_counts[record.template_id]['severity'] = record.severity
            vuln_counts[record.template_id]['name'] = record.name
        
        sorted_vulns = sorted(vuln_counts.items(), key=lambda x: x[1]['count'], reverse=True)[:limit]
        return [
            {
                'template_id': tid,
                'name': d['name'],
                'severity': d['severity'],
                'count': d['count']
            }
            for tid, d in sorted_vulns
        ]
    
    def get_top_affected_hosts(self, limit: int = 10, days: int = None) -> List[Dict]:
        """获取受影响最多的主机"""
        records = self._filter_by_days(days)
        host_stats = defaultdict(lambda: {'total': 0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0})
        
        for record in records:
            host_stats[record.host]['total'] += 1
            if record.severity in host_stats[record.host]:
                host_stats[record.host][record.severity] += 1
        
        sorted_hosts = sorted(
            host_stats.items(),
            key=lambda x: (x[1]['critical'], x[1]['high'], x[1]['total']),
            reverse=True
        )[:limit]
        
        return [{'host': host, **stats} for host, stats in sorted_hosts]
    
    def get_summary_stats(self, days: int = None) -> Dict:
        """获取汇总统计信息"""
        records = self._filter_by_days(days)
        if not records:
            return {
                'total_vulns': 0,
                'unique_vulns': 0,
                'affected_hosts': 0,
                'critical_count': 0,
                'high_count': 0,
                'severity_distribution': {}
            }
        
        severity_dist = defaultdict(int)
        unique_templates = set()
        unique_hosts = set()
        
        for record in records:
            severity_dist[record.severity] += 1
            unique_templates.add(record.template_id)
            unique_hosts.add(record.host)
        
        return {
            'total_vulns': len(records),
            'unique_vulns': len(unique_templates),
            'affected_hosts': len(unique_hosts),
            'critical_count': severity_dist.get('critical', 0),
            'high_count': severity_dist.get('high', 0),
            'severity_distribution': dict(severity_dist)
        }
    
    def _filter_by_days(self, days: int = None) -> List[VulnRecord]:
        """按天数过滤记录"""
        if days is None:
            return self._vuln_records
        cutoff = datetime.now() - timedelta(days=days)
        return [r for r in self._vuln_records if r.timestamp >= cutoff]
    
    def export_csv(self, filepath: str, days: int = None) -> bool:
        """导出漏洞数据到CSV"""
        try:
            import csv
            records = self._filter_by_days(days)
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Template', 'Name', 'Severity', 'Host', 'Matched', 'Time', 'Tags'])
                for r in records:
                    writer.writerow([
                        r.id, r.template_id, r.name, r.severity,
                        r.host, r.matched_at, r.timestamp.isoformat(),
                        ','.join(r.tags)
                    ])
            logger.info(f'Exported {len(records)} records to {filepath}')
            return True
        except Exception as e:
            logger.error(f'Export failed: {e}')
            return False
    
    def clear_old_records(self, days: int = 90):
        """清除超过指定天数的旧记录"""
        cutoff = datetime.now() - timedelta(days=days)
        old_count = len(self._vuln_records)
        self._vuln_records = [r for r in self._vuln_records if r.timestamp >= cutoff]
        removed = old_count - len(self._vuln_records)
        if removed > 0:
            self._save_history()
            logger.info(f'Cleared {removed} old records')
        return removed


_analytics_instance = None


def get_vuln_analytics() -> VulnAnalytics:
    """获取漏洞分析引擎单例"""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = VulnAnalytics()
    return _analytics_instance