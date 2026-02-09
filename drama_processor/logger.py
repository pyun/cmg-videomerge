"""
日志记录模块

提供统一的日志记录功能。
"""

import logging
from pathlib import Path
from typing import Optional


class ProcessingLogger:
    """处理日志记录器
    
    提供统一的日志记录接口，支持控制台和文件输出。
    """
    
    def __init__(
        self, 
        log_file: Optional[Path] = None,
        log_level: str = "INFO"
    ):
        """初始化日志记录器
        
        Args:
            log_file: 日志文件路径（可选）
            log_level: 日志级别
        """
        self.logger = logging.getLogger("drama_processor")
        self.logger.setLevel(getattr(logging, log_level))
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            self.logger.addHandler(file_handler)
    
    def log_task_start(self, task_type: str, drama_dir: Path) -> None:
        """记录任务开始
        
        Args:
            task_type: 任务类型
            drama_dir: 短剧目录路径
        """
        self.logger.info(f"开始 {task_type} 任务: {drama_dir}")
    
    def log_task_complete(
        self, 
        task_type: str, 
        drama_dir: Path, 
        duration: float
    ) -> None:
        """记录任务完成
        
        Args:
            task_type: 任务类型
            drama_dir: 短剧目录路径
            duration: 耗时（秒）
        """
        self.logger.info(
            f"完成 {task_type} 任务: {drama_dir} (耗时: {duration:.2f}秒)"
        )
    
    def log_task_error(
        self, 
        task_type: str, 
        drama_dir: Path, 
        error: Exception
    ) -> None:
        """记录任务错误
        
        Args:
            task_type: 任务类型
            drama_dir: 短剧目录路径
            error: 异常对象
        """
        self.logger.error(
            f"任务失败 {task_type}: {drama_dir} - {str(error)}",
            exc_info=True
        )
    
    def log_validation_error(self, drama_dir: Path, reason: str) -> None:
        """记录验证错误
        
        Args:
            drama_dir: 短剧目录路径
            reason: 错误原因
        """
        self.logger.warning(f"验证失败: {drama_dir} - {reason}")
    
    def log_batch_summary(
        self, 
        total: int, 
        success: int, 
        failed: int
    ) -> None:
        """记录批量处理摘要
        
        Args:
            total: 总任务数
            success: 成功数
            failed: 失败数
        """
        self.logger.info(
            f"批量处理完成 - 总计: {total}, 成功: {success}, 失败: {failed}"
        )
