"""
进度跟踪模块

跟踪和显示处理进度。
"""

from typing import Optional

from .interfaces import ProgressCallback
from .models import ProgressInfo, ProcessingResult


class ProgressTracker(ProgressCallback):
    """进度跟踪器
    
    实现 ProgressCallback 接口，跟踪和显示处理进度。
    """
    
    def __init__(self, show_progress: bool = True):
        """初始化进度跟踪器
        
        Args:
            show_progress: 是否显示进度信息
        """
        self.show_progress = show_progress
        self.current = 0
        self.total = 0
        self.current_file = ""
    
    def on_progress(self, info: ProgressInfo) -> None:
        """进度更新回调
        
        Args:
            info: 进度信息对象
        """
        self.current = info.current
        self.total = info.total
        self.current_file = info.current_file
        
        if self.show_progress and self.total > 0:
            percentage = (self.current / self.total) * 100
            print(f"\r进度: {self.current}/{self.total} ({percentage:.1f}%) - {self.current_file}", end="", flush=True)
    
    def on_file_start(self, filename: str) -> None:
        """文件开始处理回调
        
        Args:
            filename: 开始处理的文件名
        """
        self.current_file = filename
        if self.show_progress:
            print(f"\n开始处理: {filename}")
    
    def on_file_complete(self, result: ProcessingResult) -> None:
        """文件处理完成回调
        
        Args:
            result: 处理结果对象
        """
        if self.show_progress:
            status_text = "✓" if result.status.value == "completed" else "✗"
            print(f"\n{status_text} 完成: {result.input_path.name} - {result.status.value}")
            if result.error_message:
                print(f"  错误: {result.error_message}")
    
    def get_progress_percentage(self) -> float:
        """获取进度百分比
        
        Returns:
            进度百分比 (0-100)
        """
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100
    
    def reset(self) -> None:
        """重置进度跟踪器"""
        self.current = 0
        self.total = 0
        self.current_file = ""

