"""
错误处理模块

提供错误分类、处理和恢复机制。
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable


class ValidationError(Exception):
    """验证错误
    
    当输入验证失败时抛出。
    """
    pass


class FFmpegError(Exception):
    """FFmpeg 执行错误
    
    当 FFmpeg 命令执行失败时抛出。
    """
    pass


class AudioSeparationError(Exception):
    """音频分离错误
    
    当音频分离处理失败时抛出。
    """
    pass


class ErrorRecoveryStrategy(ABC):
    """错误恢复策略基类"""
    
    @abstractmethod
    def can_recover(self, error: Exception) -> bool:
        """判断错误是否可恢复
        
        Args:
            error: 异常对象
            
        Returns:
            是否可以恢复
        """
        pass
    
    @abstractmethod
    def recover(self, error: Exception, context: Dict[str, Any]) -> bool:
        """尝试恢复
        
        Args:
            error: 异常对象
            context: 上下文信息
            
        Returns:
            是否恢复成功
        """
        pass


class RetryStrategy(ErrorRecoveryStrategy):
    """重试策略"""
    
    def __init__(self, max_retries: int = 3, delay_seconds: float = 1.0):
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
    
    def can_recover(self, error: Exception) -> bool:
        """判断错误是否可恢复
        
        网络错误、临时文件锁、IO错误等可以重试
        """
        # 可恢复的错误类型
        recoverable_types = (IOError, OSError, TimeoutError)
        return isinstance(error, recoverable_types)
    
    def recover(self, error: Exception, context: Dict[str, Any]) -> bool:
        """尝试恢复
        
        Args:
            error: 异常对象
            context: 上下文信息，应包含 'retry_count' 和 'operation' 键
            
        Returns:
            是否恢复成功
        """
        retry_count = context.get('retry_count', 0)
        
        if retry_count >= self.max_retries:
            return False
        
        # 等待后重试
        time.sleep(self.delay_seconds * (retry_count + 1))  # 指数退避
        
        # 尝试重新执行操作
        operation = context.get('operation')
        if operation and callable(operation):
            try:
                operation()
                return True
            except Exception:
                context['retry_count'] = retry_count + 1
                return self.recover(error, context)
        
        return False


class SkipStrategy(ErrorRecoveryStrategy):
    """跳过策略"""
    
    def can_recover(self, error: Exception) -> bool:
        """判断错误是否可恢复
        
        输入验证错误应该跳过，不需要重试
        """
        return isinstance(error, ValidationError)
    
    def recover(self, error: Exception, context: Dict[str, Any]) -> bool:
        """尝试恢复
        
        对于验证错误，直接跳过并记录
        
        Args:
            error: 异常对象
            context: 上下文信息
            
        Returns:
            总是返回 True，表示通过跳过来"恢复"
        """
        # 记录跳过信息
        if 'logger' in context:
            logger = context['logger']
            logger.warning(f"跳过处理: {str(error)}")
        
        return True


class ErrorHandler:
    """错误处理器
    
    管理错误恢复策略，处理各种类型的错误。
    """
    
    def __init__(self):
        self.strategies = []
    
    def add_strategy(self, strategy: ErrorRecoveryStrategy) -> None:
        """添加恢复策略
        
        Args:
            strategy: 恢复策略对象
        """
        self.strategies.append(strategy)
    
    def handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        """处理错误
        
        尝试使用已注册的策略恢复错误
        
        Args:
            error: 异常对象
            context: 上下文信息
            
        Returns:
            是否成功处理（恢复或跳过）
        """
        # 尝试每个策略
        for strategy in self.strategies:
            if strategy.can_recover(error):
                try:
                    if strategy.recover(error, context):
                        return True
                except Exception as recovery_error:
                    # 恢复过程本身失败，继续尝试下一个策略
                    if 'logger' in context:
                        logger = context['logger']
                        logger.warning(f"恢复策略失败: {str(recovery_error)}")
                    continue
        
        # 所有策略都失败
        return False
