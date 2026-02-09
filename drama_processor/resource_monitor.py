"""资源监控模块

提供 CPU 和内存使用监控功能，记录峰值使用情况。
"""

import time
from dataclasses import dataclass
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float
    memory_mb: float
    peak_memory_mb: float
    elapsed_seconds: float


class ResourceMonitor:
    """资源监控器
    
    监控当前进程的 CPU 和内存使用情况，记录峰值。
    """
    
    def __init__(self):
        """初始化资源监控器"""
        if psutil is None:
            raise ImportError(
                "psutil 库未安装。请运行: pip install psutil"
            )
        
        self.start_time = time.time()
        self.peak_memory = 0.0
        self._process = psutil.Process()
    
    def update(self) -> ResourceUsage:
        """更新并返回当前资源使用情况
        
        Returns:
            ResourceUsage: 包含 CPU、内存使用和峰值信息
        """
        # 获取内存使用（MB）
        memory_mb = self._process.memory_info().rss / (1024 * 1024)
        
        # 更新峰值内存
        self.peak_memory = max(self.peak_memory, memory_mb)
        
        # 获取 CPU 使用率（百分比）
        cpu_percent = self._process.cpu_percent(interval=0.1)
        
        # 计算运行时间
        elapsed_seconds = time.time() - self.start_time
        
        return ResourceUsage(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            peak_memory_mb=self.peak_memory,
            elapsed_seconds=elapsed_seconds
        )
    
    def get_current_usage(self) -> ResourceUsage:
        """获取当前资源使用情况（不更新峰值）
        
        Returns:
            ResourceUsage: 当前资源使用情况
        """
        memory_mb = self._process.memory_info().rss / (1024 * 1024)
        cpu_percent = self._process.cpu_percent(interval=0.1)
        elapsed_seconds = time.time() - self.start_time
        
        return ResourceUsage(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            peak_memory_mb=self.peak_memory,
            elapsed_seconds=elapsed_seconds
        )
    
    def reset(self) -> None:
        """重置监控器（重置开始时间和峰值内存）"""
        self.start_time = time.time()
        self.peak_memory = 0.0
    
    def get_peak_memory(self) -> float:
        """获取峰值内存使用（MB）
        
        Returns:
            float: 峰值内存使用（MB）
        """
        return self.peak_memory
    
    def get_elapsed_time(self) -> float:
        """获取运行时间（秒）
        
        Returns:
            float: 从开始到现在的运行时间（秒）
        """
        return time.time() - self.start_time
    
    def format_usage(self, usage: Optional[ResourceUsage] = None) -> str:
        """格式化资源使用信息为可读字符串
        
        Args:
            usage: 资源使用情况，如果为 None 则获取当前使用情况
        
        Returns:
            str: 格式化的资源使用信息
        """
        if usage is None:
            usage = self.get_current_usage()
        
        return (
            f"CPU: {usage.cpu_percent:.1f}%, "
            f"内存: {usage.memory_mb:.1f}MB, "
            f"峰值内存: {usage.peak_memory_mb:.1f}MB, "
            f"运行时间: {usage.elapsed_seconds:.1f}秒"
        )
