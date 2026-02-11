"""
扫描代理池模块
支持多代理轮换，避免IP封禁
"""
import random
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from core.logger import get_logger

logger = get_logger('proxy_pool')


class ProxyStatus(Enum):
    ACTIVE = 'active'
    FAILED = 'failed'
    COOLDOWN = 'cooldown'
    DISABLED = 'disabled'


@dataclass
class ProxyInfo:
    url: str
    protocol: str = 'http'
    status: ProxyStatus = ProxyStatus.ACTIVE
    success_count: int = 0
    fail_count: int = 0
    last_used: datetime = None
    cooldown_until: datetime = None
    response_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 1.0
    
    def mark_success(self, response_time: float = 0.0):
        self.success_count += 1
        self.last_used = datetime.now()
        self.response_time = response_time
        self.status = ProxyStatus.ACTIVE
    
    def mark_failure(self, cooldown_seconds: int = 60):
        self.fail_count += 1
        self.last_used = datetime.now()
        if self.fail_count >= 3 and self.success_rate < 0.5:
            self.status = ProxyStatus.COOLDOWN
            self.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
    
    def is_available(self) -> bool:
        if self.status == ProxyStatus.DISABLED:
            return False
        if self.status == ProxyStatus.COOLDOWN:
            if self.cooldown_until and datetime.now() >= self.cooldown_until:
                self.status = ProxyStatus.ACTIVE
                self.fail_count = 0
                return True
            return False
        return True


class ProxyPool:
    """代理池管理器"""
    
    def __init__(self):
        self._proxies: List[ProxyInfo] = []
        self._lock = threading.Lock()
        self._current_index = 0
        self._rotation_mode = 'round_robin'
    
    def add_proxy(self, url: str, protocol: str = 'http') -> bool:
        """添加代理"""
        with self._lock:
            if any(p.url == url for p in self._proxies):
                return False
            self._proxies.append(ProxyInfo(url=url, protocol=protocol))
            logger.info(f'Added proxy: {url}')
            return True
    
    def add_proxies_from_list(self, proxy_list: List[str]):
        """从列表批量添加代理"""
        for proxy in proxy_list:
            proxy = proxy.strip()
            if proxy:
                if '://' in proxy:
                    protocol, url = proxy.split('://', 1)
                    self.add_proxy(url, protocol)
                else:
                    self.add_proxy(proxy)
    
    def remove_proxy(self, url: str) -> bool:
        """移除代理"""
        with self._lock:
            for i, p in enumerate(self._proxies):
                if p.url == url:
                    self._proxies.pop(i)
                    return True
            return False
    
    def get_next_proxy(self) -> Optional[str]:
        """获取下一个可用代理"""
        with self._lock:
            available = [p for p in self._proxies if p.is_available()]
            if not available:
                return None
            
            if self._rotation_mode == 'round_robin':
                self._current_index = (self._current_index + 1) % len(available)
                proxy = available[self._current_index]
            elif self._rotation_mode == 'random':
                proxy = random.choice(available)
            elif self._rotation_mode == 'best':
                proxy = max(available, key=lambda p: (p.success_rate, -p.response_time))
            else:
                proxy = available[0]
            
            return f'{proxy.protocol}://{proxy.url}'
    
    def report_success(self, proxy_url: str, response_time: float = 0.0):
        """报告代理成功"""
        with self._lock:
            for p in self._proxies:
                if proxy_url.endswith(p.url):
                    p.mark_success(response_time)
                    break
    
    def report_failure(self, proxy_url: str):
        """报告代理失败"""
        with self._lock:
            for p in self._proxies:
                if proxy_url.endswith(p.url):
                    p.mark_failure()
                    logger.warning(f'Proxy failed: {p.url}')
                    break
    
    def set_rotation_mode(self, mode: str):
        """设置轮换模式: round_robin, random, best"""
        if mode in ['round_robin', 'random', 'best']:
            self._rotation_mode = mode
    
    def get_stats(self) -> Dict:
        """获取代理池统计"""
        with self._lock:
            return {
                'total': len(self._proxies),
                'active': sum(1 for p in self._proxies if p.status == ProxyStatus.ACTIVE),
                'cooldown': sum(1 for p in self._proxies if p.status == ProxyStatus.COOLDOWN),
                'disabled': sum(1 for p in self._proxies if p.status == ProxyStatus.DISABLED),
                'proxies': [
                    {
                        'url': p.url,
                        'status': p.status.value,
                        'success_rate': round(p.success_rate * 100, 1),
                        'response_time': round(p.response_time, 2)
                    }
                    for p in self._proxies
                ]
            }
    
    def clear(self):
        """清空代理池"""
        with self._lock:
            self._proxies.clear()
            self._current_index = 0


_proxy_pool = None


def get_proxy_pool() -> ProxyPool:
    """获取代理池单例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool()
    return _proxy_pool
