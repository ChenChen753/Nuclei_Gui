"""
性能监控模块
实时监控CPU、内存、网络使用情况
"""
import threading
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
from collections import deque

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from core.logger import get_logger

logger = get_logger('perf_monitor')


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    timestamp: datetime
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    active_threads: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': round(self.cpu_percent, 1),
            'memory_percent': round(self.memory_percent, 1),
            'memory_used_mb': round(self.memory_used_mb, 1),
            'network_sent_mb': round(self.network_sent_mb, 2),
            'network_recv_mb': round(self.network_recv_mb, 2),
            'active_threads': self.active_threads
        }


class PerformanceMonitor(QObject):
    """性能监控器"""
    
    stats_updated = pyqtSignal(dict)
    alert_triggered = pyqtSignal(str, str)
    
    DEFAULT_THRESHOLDS = {
        'cpu_warning': 80,
        'cpu_critical': 95,
        'memory_warning': 80,
        'memory_critical': 95
    }
    
    def __init__(self, history_size: int = 300):
        super().__init__()
        self._history_size = history_size
        self._history: deque = deque(maxlen=history_size)
        self._is_running = False
        self._timer = None
        self._thresholds = self.DEFAULT_THRESHOLDS.copy()
        self._last_net_io = None
        self._psutil_available = self._check_psutil()
    
    def _check_psutil(self) -> bool:
        try:
            import psutil
            return True
        except ImportError:
            logger.warning('psutil not installed')
            return False
    
    def start(self, interval_ms: int = 1000):
        if self._is_running:
            return
        self._is_running = True
        self._timer = QTimer()
        self._timer.timeout.connect(self._collect_stats)
        self._timer.start(interval_ms)
        logger.info('Performance monitor started')
    
    def stop(self):
        self._is_running = False
        if self._timer:
            self._timer.stop()
            self._timer = None
        logger.info('Performance monitor stopped')
    
    def _collect_stats(self):
        try:
            snapshot = self._get_snapshot()
            self._history.append(snapshot)
            self.stats_updated.emit(snapshot.to_dict())
            self._check_alerts(snapshot)
        except Exception as e:
            logger.error(f'Failed to collect stats: {e}')
    
    def _get_snapshot(self) -> PerformanceSnapshot:
        snapshot = PerformanceSnapshot(timestamp=datetime.now())
        
        if self._psutil_available:
            import psutil
            snapshot.cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            snapshot.memory_percent = mem.percent
            snapshot.memory_used_mb = mem.used / (1024 * 1024)
            snapshot.memory_available_mb = mem.available / (1024 * 1024)
            
            net_io = psutil.net_io_counters()
            if self._last_net_io:
                snapshot.network_sent_mb = (net_io.bytes_sent - self._last_net_io.bytes_sent) / (1024 * 1024)
                snapshot.network_recv_mb = (net_io.bytes_recv - self._last_net_io.bytes_recv) / (1024 * 1024)
            self._last_net_io = net_io
        
        snapshot.active_threads = threading.active_count()
        return snapshot
    
    def _check_alerts(self, snapshot: PerformanceSnapshot):
        if snapshot.cpu_percent >= self._thresholds['cpu_critical']:
            self.alert_triggered.emit('critical', f'CPU过高: {snapshot.cpu_percent}%')
        elif snapshot.cpu_percent >= self._thresholds['cpu_warning']:
            self.alert_triggered.emit('warning', f'CPU较高: {snapshot.cpu_percent}%')
        
        if snapshot.memory_percent >= self._thresholds['memory_critical']:
            self.alert_triggered.emit('critical', f'内存过高: {snapshot.memory_percent}%')
        elif snapshot.memory_percent >= self._thresholds['memory_warning']:
            self.alert_triggered.emit('warning', f'内存较高: {snapshot.memory_percent}%')
    
    def set_thresholds(self, thresholds: Dict):
        self._thresholds.update(thresholds)
    
    def get_current_stats(self) -> Dict:
        if self._history:
            return self._history[-1].to_dict()
        return {}
    
    def get_history(self, count: int = None) -> List[Dict]:
        if count:
            return [s.to_dict() for s in list(self._history)[-count:]]
        return [s.to_dict() for s in self._history]
    
    def get_average_stats(self, seconds: int = 60) -> Dict:
        if not self._history:
            return {}
        
        recent = list(self._history)[-seconds:]
        if not recent:
            return {}
        
        return {
            'cpu_percent': round(sum(s.cpu_percent for s in recent) / len(recent), 1),
            'memory_percent': round(sum(s.memory_percent for s in recent) / len(recent), 1),
            'samples': len(recent)
        }


_monitor_instance = None


def get_perf_monitor() -> PerformanceMonitor:
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance
