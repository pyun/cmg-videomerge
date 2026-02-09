"""
任务编排器

协调各个处理模块的执行，管理批量处理流程。
"""

import time
from pathlib import Path
from typing import List, Optional, Dict

from .interfaces import ProgressCallback
from .models import ProcessingResult, ProcessingStatus, ProgressInfo
from .merger import VideoMerger
from .separator import AudioSeparator
from .transcoder import VideoTranscoder
from .scanner import DirectoryScanner
from .logger import ProcessingLogger
from .error_handler import ErrorHandler, ValidationError


class Orchestrator:
    """任务编排器
    
    协调视频合并、音频分离、视频转码等模块的执行。
    """
    
    def __init__(
        self,
        logger: Optional[ProcessingLogger] = None,
        error_handler: Optional[ErrorHandler] = None,
        audio_separator_model: str = "spleeter:2stems",
        accompaniment_volume: float = 0.0,
        transcode_specs: Optional[List] = None
    ):
        """初始化编排器
        
        Args:
            logger: 日志记录器
            error_handler: 错误处理器
            audio_separator_model: 音频分离模型
            accompaniment_volume: 伴奏保留音量（0.0-1.0）
            transcode_specs: 转码规格列表
        """
        self.merger = VideoMerger()
        self.separator = AudioSeparator(
            model=audio_separator_model,
            accompaniment_volume=accompaniment_volume
        )
        self.transcoder = VideoTranscoder(specs=transcode_specs)
        self.scanner = DirectoryScanner()
        self.logger = logger or ProcessingLogger()
        self.error_handler = error_handler or ErrorHandler()
    
    def merge(
        self, 
        drama_dir: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """执行视频合并
        
        Args:
            drama_dir: 短剧目录路径
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果
        """
        start_time = time.time()
        self.logger.log_task_start("merge", drama_dir)
        
        try:
            # 验证目录结构
            drama_info = self.scanner.scan_drama_root(drama_dir.parent)
            matching_dirs = [d for d in drama_info if d.path == drama_dir]
            
            if not matching_dirs:
                raise ValidationError(f"目录不符合 drama-XXXX 命名模式: {drama_dir}")
            
            drama = matching_dirs[0]
            if not self.scanner.validate_for_merge(drama):
                raise ValidationError(f"目录结构不适合合并操作: {drama_dir}")
            
            # 执行合并
            result = self.merger.process(drama_dir, progress_callback)
            
            duration = time.time() - start_time
            self.logger.log_task_complete("merge", drama_dir, duration)
            
            return result
            
        except Exception as e:
            self.logger.log_task_error("merge", drama_dir, e)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                input_path=drama_dir,
                output_path=None,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
    
    def separate(
        self, 
        drama_dir: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """执行音频分离
        
        Args:
            drama_dir: 短剧目录路径
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果
        """
        start_time = time.time()
        self.logger.log_task_start("separate", drama_dir)
        
        try:
            # 验证目录结构
            drama_info = self.scanner.scan_drama_root(drama_dir.parent)
            matching_dirs = [d for d in drama_info if d.path == drama_dir]
            
            if not matching_dirs:
                raise ValidationError(f"目录不符合 drama-XXXX 命名模式: {drama_dir}")
            
            drama = matching_dirs[0]
            if not self.scanner.validate_for_separation(drama):
                raise ValidationError(f"目录结构不适合音频分离操作: {drama_dir}")
            
            # 执行音频分离
            result = self.separator.process(drama_dir, progress_callback)
            
            duration = time.time() - start_time
            self.logger.log_task_complete("separate", drama_dir, duration)
            
            return result
            
        except Exception as e:
            self.logger.log_task_error("separate", drama_dir, e)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                input_path=drama_dir,
                output_path=None,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
    
    def transcode(
        self, 
        drama_dir: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """执行视频转码
        
        Args:
            drama_dir: 短剧目录路径
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果
        """
        start_time = time.time()
        self.logger.log_task_start("transcode", drama_dir)
        
        try:
            # 验证目录结构
            drama_info = self.scanner.scan_drama_root(drama_dir.parent)
            matching_dirs = [d for d in drama_info if d.path == drama_dir]
            
            if not matching_dirs:
                raise ValidationError(f"目录不符合 drama-XXXX 命名模式: {drama_dir}")
            
            drama = matching_dirs[0]
            if not self.scanner.validate_for_transcode(drama):
                raise ValidationError(f"目录结构不适合转码操作: {drama_dir}")
            
            # 执行转码
            result = self.transcoder.process(drama_dir, progress_callback)
            
            duration = time.time() - start_time
            self.logger.log_task_complete("transcode", drama_dir, duration)
            
            return result
            
        except Exception as e:
            self.logger.log_task_error("transcode", drama_dir, e)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                input_path=drama_dir,
                output_path=None,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
    
    def process_batch(
        self,
        drama_dirs: List[Path],
        operation: str = "merge",
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ProcessingResult]:
        """批量处理多个短剧目录
        
        Args:
            drama_dirs: 短剧目录路径列表
            operation: 操作类型 ("merge", "separate", "transcode")
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果列表
        """
        results = []
        total = len(drama_dirs)
        
        # 选择操作方法
        operation_map = {
            "merge": self.merge,
            "separate": self.separate,
            "transcode": self.transcode
        }
        
        if operation not in operation_map:
            raise ValueError(f"不支持的操作类型: {operation}")
        
        operation_func = operation_map[operation]
        
        # 处理每个目录
        for i, drama_dir in enumerate(drama_dirs):
            # 更新进度
            if progress_callback:
                progress_info = ProgressInfo(
                    current=i,
                    total=total,
                    current_file=drama_dir.name,
                    percentage=(i / total) * 100 if total > 0 else 0
                )
                progress_callback.on_progress(progress_info)
                progress_callback.on_file_start(drama_dir.name)
            
            # 执行操作
            result = operation_func(drama_dir, progress_callback)
            results.append(result)
            
            # 通知完成
            if progress_callback:
                progress_callback.on_file_complete(result)
        
        # 最终进度更新
        if progress_callback:
            progress_info = ProgressInfo(
                current=total,
                total=total,
                current_file="",
                percentage=100.0
            )
            progress_callback.on_progress(progress_info)
        
        # 记录批量处理摘要
        success_count = sum(1 for r in results if r.status == ProcessingStatus.COMPLETED)
        failed_count = sum(1 for r in results if r.status == ProcessingStatus.FAILED)
        self.logger.log_batch_summary(total, success_count, failed_count)
        
        return results



class ConcurrentOrchestrator(Orchestrator):
    """并发任务编排器
    
    使用线程池并发处理多个短剧目录。
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        logger: Optional[ProcessingLogger] = None,
        error_handler: Optional[ErrorHandler] = None,
        audio_separator_model: str = "spleeter:2stems",
        accompaniment_volume: float = 0.0,
        transcode_specs: Optional[List] = None
    ):
        """初始化并发编排器
        
        Args:
            max_workers: 最大并发工作线程数
            logger: 日志记录器
            error_handler: 错误处理器
            audio_separator_model: 音频分离模型
            accompaniment_volume: 伴奏保留音量（0.0-1.0）
            transcode_specs: 转码规格列表
        """
        super().__init__(logger, error_handler, audio_separator_model, accompaniment_volume, transcode_specs)
        self.max_workers = max_workers
        self._lock = None  # 延迟初始化,避免序列化问题
    
    def _get_lock(self):
        """获取线程锁(延迟初始化)"""
        if self._lock is None:
            import threading
            self._lock = threading.Lock()
        return self._lock
    
    def process_batch(
        self,
        drama_dirs: List[Path],
        operation: str = "merge",
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ProcessingResult]:
        """并发批量处理多个短剧目录
        
        Args:
            drama_dirs: 短剧目录路径列表
            operation: 操作类型 ("merge", "separate", "transcode")
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = [None] * len(drama_dirs)  # 预分配结果列表
        total = len(drama_dirs)
        completed_count = [0]  # 使用列表以便在闭包中修改
        
        # 选择操作方法
        operation_map = {
            "merge": self.merge,
            "separate": self.separate,
            "transcode": self.transcode
        }
        
        if operation not in operation_map:
            raise ValueError(f"不支持的操作类型: {operation}")
        
        operation_func = operation_map[operation]
        
        def process_single(index: int, drama_dir: Path) -> tuple[int, ProcessingResult]:
            """处理单个目录并返回索引和结果"""
            # 通知开始
            if progress_callback:
                with self._get_lock():
                    progress_callback.on_file_start(drama_dir.name)
            
            # 执行操作
            result = operation_func(drama_dir, None)  # 不传递进度回调,避免冲突
            
            # 线程安全的进度更新
            if progress_callback:
                with self._get_lock():
                    completed_count[0] += 1
                    progress_info = ProgressInfo(
                        current=completed_count[0],
                        total=total,
                        current_file=drama_dir.name,
                        percentage=(completed_count[0] / total) * 100 if total > 0 else 0
                    )
                    progress_callback.on_progress(progress_info)
                    progress_callback.on_file_complete(result)
            
            return index, result
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(process_single, i, drama_dir): i
                for i, drama_dir in enumerate(drama_dirs)
            }
            
            # 收集结果
            for future in as_completed(futures):
                try:
                    index, result = future.result()
                    results[index] = result
                except Exception as e:
                    # 处理未预期的异常
                    index = futures[future]
                    drama_dir = drama_dirs[index]
                    self.logger.log_task_error(operation, drama_dir, e)
                    results[index] = ProcessingResult(
                        status=ProcessingStatus.FAILED,
                        input_path=drama_dir,
                        output_path=None,
                        error_message=str(e),
                        duration_seconds=0.0
                    )
        
        # 记录批量处理摘要
        success_count = sum(1 for r in results if r and r.status == ProcessingStatus.COMPLETED)
        failed_count = sum(1 for r in results if r and r.status == ProcessingStatus.FAILED)
        self.logger.log_batch_summary(total, success_count, failed_count)
        
        return results



class ResumableOrchestrator(Orchestrator):
    """支持断点续传的任务编排器
    
    使用状态管理器跟踪已完成的任务,支持断点续传。
    """
    
    def __init__(
        self,
        state_file: Path,
        logger: Optional[ProcessingLogger] = None,
        error_handler: Optional[ErrorHandler] = None,
        audio_separator_model: str = "spleeter:2stems",
        accompaniment_volume: float = 0.0,
        transcode_specs: Optional[List] = None
    ):
        """初始化可续传编排器
        
        Args:
            state_file: 状态文件路径
            logger: 日志记录器
            error_handler: 错误处理器
            audio_separator_model: 音频分离模型
            accompaniment_volume: 伴奏保留音量（0.0-1.0）
            transcode_specs: 转码规格列表
        """
        super().__init__(logger, error_handler, audio_separator_model, accompaniment_volume, transcode_specs)
        from .state import StateManager
        self.state_manager = StateManager(state_file)
    
    def process_batch(
        self,
        drama_dirs: List[Path],
        operation: str = "merge",
        progress_callback: Optional[ProgressCallback] = None,
        skip_completed: bool = True
    ) -> List[ProcessingResult]:
        """批量处理多个短剧目录(支持断点续传)
        
        Args:
            drama_dirs: 短剧目录路径列表
            operation: 操作类型 ("merge", "separate", "transcode")
            progress_callback: 可选的进度回调对象
            skip_completed: 是否跳过已完成的任务
            
        Returns:
            处理结果列表
        """
        # 过滤已完成的任务
        if skip_completed:
            pending_dirs = self.state_manager.get_pending_tasks(drama_dirs, operation)
            skipped_count = len(drama_dirs) - len(pending_dirs)
            
            if skipped_count > 0:
                self.logger.logger.info(f"跳过 {skipped_count} 个已完成的任务")
            
            drama_dirs = pending_dirs
        
        # 如果没有待处理任务,直接返回
        if not drama_dirs:
            return []
        
        # 调用父类的批量处理方法
        results = super().process_batch(drama_dirs, operation, progress_callback)
        
        # 更新状态
        for result in results:
            if result.status == ProcessingStatus.COMPLETED:
                output_files = [result.output_path] if result.output_path else []
                self.state_manager.mark_completed(
                    result.input_path,
                    operation,
                    output_files
                )
            elif result.status == ProcessingStatus.FAILED:
                self.state_manager.mark_failed(
                    result.input_path,
                    operation,
                    result.error_message or "未知错误"
                )
        
        return results
    
    def get_summary(self) -> Dict:
        """获取处理摘要
        
        Returns:
            包含统计信息的字典
        """
        return self.state_manager.get_summary()



class ReportingOrchestrator(Orchestrator):
    """支持详细报告的任务编排器
    
    生成详细的处理报告并保存到文件。
    """
    
    def __init__(
        self,
        report_dir: Path,
        logger: Optional[ProcessingLogger] = None,
        error_handler: Optional[ErrorHandler] = None,
        audio_separator_model: str = "spleeter:2stems",
        accompaniment_volume: float = 0.0,
        transcode_specs: Optional[List] = None
    ):
        """初始化报告编排器
        
        Args:
            report_dir: 报告输出目录
            logger: 日志记录器
            error_handler: 错误处理器
            audio_separator_model: 音频分离模型
            accompaniment_volume: 伴奏保留音量（0.0-1.0）
            transcode_specs: 转码规格列表
        """
        super().__init__(logger, error_handler, audio_separator_model, accompaniment_volume, transcode_specs)
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def process_batch(
        self,
        drama_dirs: List[Path],
        operation: str = "merge",
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ProcessingResult]:
        """批量处理多个短剧目录(生成详细报告)
        
        Args:
            drama_dirs: 短剧目录路径列表
            operation: 操作类型 ("merge", "separate", "transcode")
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果列表
        """
        from datetime import datetime
        from .report import DetailedProcessingReport
        
        # 创建报告
        report = DetailedProcessingReport(
            operation=operation,
            start_time=datetime.now(),
            total_tasks=len(drama_dirs)
        )
        
        # 调用父类的批量处理方法
        results = super().process_batch(drama_dirs, operation, progress_callback)
        
        # 收集结果
        for result in results:
            if result.status == ProcessingStatus.COMPLETED:
                report.successful_tasks.append(str(result.input_path))
            elif result.status == ProcessingStatus.FAILED:
                report.failed_tasks.append((
                    str(result.input_path),
                    result.error_message or "未知错误"
                ))
            elif result.status == ProcessingStatus.SKIPPED:
                report.skipped_tasks.append((
                    str(result.input_path),
                    result.error_message or "已跳过"
                ))
        
        # 设置结束时间
        report.end_time = datetime.now()
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_dir / f"{operation}_report_{timestamp}.json"
        report.save_to_file(report_file)
        
        # 打印摘要
        report.print_summary()
        
        self.logger.logger.info(f"报告已保存到: {report_file}")
        
        return results
