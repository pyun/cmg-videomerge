"""
基础接口定义

本模块定义了短剧视频批量处理工具的核心接口，包括：
- ProgressCallback: 进度回调接口
- VideoProcessor: 视频处理器基类

所有具体的处理模块（合并、分离、转码）都应该继承 VideoProcessor 基类。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from .models import ProcessingResult, ProgressInfo


class ProgressCallback(ABC):
    """进度回调接口
    
    用于接收处理进度更新的抽象基类。
    实现此接口以自定义进度显示方式。
    """
    
    @abstractmethod
    def on_progress(self, info: ProgressInfo) -> None:
        """进度更新回调
        
        当处理进度更新时调用。
        
        Args:
            info: 进度信息对象
        """
        pass
    
    @abstractmethod
    def on_file_start(self, filename: str) -> None:
        """文件开始处理回调
        
        当开始处理一个新文件时调用。
        
        Args:
            filename: 开始处理的文件名
        """
        pass
    
    @abstractmethod
    def on_file_complete(self, result: ProcessingResult) -> None:
        """文件处理完成回调
        
        当一个文件处理完成时调用。
        
        Args:
            result: 处理结果对象
        """
        pass


class VideoProcessor(ABC):
    """视频处理器基类
    
    所有视频处理模块的抽象基类。
    具体的处理模块（VideoMerger, AudioSeparator, VideoTranscoder）
    应该继承此类并实现抽象方法。
    """
    
    @abstractmethod
    def process(
        self, 
        drama_dir: Path, 
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """处理单个短剧目录
        
        Args:
            drama_dir: 短剧目录路径
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果对象
        """
        pass
    
    @abstractmethod
    def process_batch(
        self, 
        drama_dirs: List[Path],
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ProcessingResult]:
        """批量处理多个短剧目录
        
        Args:
            drama_dirs: 短剧目录路径列表
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果列表，与输入目录一一对应
        """
        pass
