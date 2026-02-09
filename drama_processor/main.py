"""
主程序入口模块

提供三个主要功能的入口函数：
1. run_merge: 执行视频合并
2. run_separate: 执行音频分离
3. run_transcode: 执行视频转码
"""

from pathlib import Path
from typing import List, Optional

from .models import ProcessingConfig, ProcessingStatus
from .orchestrator import (
    Orchestrator,
    ConcurrentOrchestrator,
    ResumableOrchestrator,
    ReportingOrchestrator
)
from .scanner import DirectoryScanner
from .logger import ProcessingLogger
from .progress import ProgressTracker
from .error_handler import ErrorHandler


def create_orchestrator(config: ProcessingConfig) -> Orchestrator:
    """根据配置创建合适的编排器
    
    根据配置选项创建不同功能组合的编排器：
    - 基础编排器：单线程处理
    - 并发编排器：多线程并发处理
    - 可续传编排器：支持断点续传
    - 报告编排器：生成详细报告
    
    Args:
        config: 处理配置对象
        
    Returns:
        配置好的编排器实例
    """
    # 初始化日志记录器
    logger = ProcessingLogger(
        log_file=config.log_file,
        log_level=config.log_level
    )
    
    # 初始化错误处理器
    error_handler = ErrorHandler()
    
    # 根据配置选择编排器类型
    if config.max_workers > 1:
        # 使用并发编排器
        orchestrator = ConcurrentOrchestrator(
            max_workers=config.max_workers,
            logger=logger,
            error_handler=error_handler,
            audio_separator_model=config.audio_separator_model,
            accompaniment_volume=config.accompaniment_volume,
            transcode_specs=config.transcode_specs
        )
    else:
        # 使用基础编排器
        orchestrator = Orchestrator(
            logger=logger,
            error_handler=error_handler,
            audio_separator_model=config.audio_separator_model,
            accompaniment_volume=config.accompaniment_volume,
            transcode_specs=config.transcode_specs
        )
    
    # 如果启用断点续传，包装为可续传编排器
    if config.enable_resume:
        from .state import StateManager
        state_manager = StateManager(config.state_file)
        
        # 创建一个混合类，同时支持并发和断点续传
        class ConcurrentResumableOrchestrator(ResumableOrchestrator):
            """同时支持并发和断点续传的编排器"""
            
            def __init__(self, base_orchestrator, state_file, logger, error_handler):
                # 不调用父类的 __init__，而是直接设置属性
                self.merger = base_orchestrator.merger
                self.separator = base_orchestrator.separator
                self.transcoder = base_orchestrator.transcoder
                self.scanner = base_orchestrator.scanner
                self.logger = logger
                self.error_handler = error_handler
                self.state_manager = StateManager(state_file)
                
                # 如果是并发编排器，保留并发功能
                if isinstance(base_orchestrator, ConcurrentOrchestrator):
                    self.max_workers = base_orchestrator.max_workers
                    self._lock = None
            
            def _get_lock(self):
                """获取线程锁(延迟初始化)"""
                if not hasattr(self, '_lock') or self._lock is None:
                    import threading
                    self._lock = threading.Lock()
                return self._lock
            
            def process_batch(self, drama_dirs, operation="merge", progress_callback=None, skip_completed=True):
                """批量处理（支持并发和断点续传）"""
                # 过滤已完成的任务
                if skip_completed:
                    pending_dirs = self.state_manager.get_pending_tasks(drama_dirs, operation)
                    skipped_count = len(drama_dirs) - len(pending_dirs)
                    
                    if skipped_count > 0:
                        self.logger.logger.info(f"跳过 {skipped_count} 个已完成的任务")
                    
                    drama_dirs = pending_dirs
                
                # 如果没有待处理任务，直接返回
                if not drama_dirs:
                    return []
                
                # 根据是否有并发能力选择处理方式
                if hasattr(self, 'max_workers') and self.max_workers > 1:
                    # 使用并发处理
                    results = ConcurrentOrchestrator.process_batch(
                        self, drama_dirs, operation, progress_callback
                    )
                else:
                    # 使用串行处理
                    results = Orchestrator.process_batch(
                        self, drama_dirs, operation, progress_callback
                    )
                
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
        
        orchestrator = ConcurrentResumableOrchestrator(
            orchestrator,
            config.state_file,
            logger,
            error_handler
        )
    
    # 如果启用报告生成，包装为报告编排器
    if config.generate_report:
        # 确保报告目录存在
        config.report_dir.mkdir(parents=True, exist_ok=True)
        
        class ReportingWrapper:
            """报告包装器，为任何编排器添加报告功能"""
            
            def __init__(self, base_orchestrator, report_dir):
                self.base_orchestrator = base_orchestrator
                self.report_dir = report_dir
                # 代理所有属性
                self.merger = base_orchestrator.merger
                self.separator = base_orchestrator.separator
                self.transcoder = base_orchestrator.transcoder
                self.scanner = base_orchestrator.scanner
                self.logger = base_orchestrator.logger
                self.error_handler = base_orchestrator.error_handler
                if hasattr(base_orchestrator, 'state_manager'):
                    self.state_manager = base_orchestrator.state_manager
            
            def merge(self, drama_dir, progress_callback=None):
                return self.base_orchestrator.merge(drama_dir, progress_callback)
            
            def separate(self, drama_dir, progress_callback=None):
                return self.base_orchestrator.separate(drama_dir, progress_callback)
            
            def transcode(self, drama_dir, progress_callback=None):
                return self.base_orchestrator.transcode(drama_dir, progress_callback)
            
            def process_batch(self, drama_dirs, operation="merge", progress_callback=None, skip_completed=True):
                """批量处理并生成报告"""
                from datetime import datetime
                from .report import DetailedProcessingReport
                
                # 创建报告
                report = DetailedProcessingReport(
                    operation=operation,
                    start_time=datetime.now(),
                    total_tasks=len(drama_dirs)
                )
                
                # 调用基础编排器的批量处理
                if hasattr(self.base_orchestrator, 'process_batch'):
                    # 支持断点续传的编排器
                    if 'skip_completed' in self.base_orchestrator.process_batch.__code__.co_varnames:
                        results = self.base_orchestrator.process_batch(
                            drama_dirs, operation, progress_callback, skip_completed
                        )
                    else:
                        results = self.base_orchestrator.process_batch(
                            drama_dirs, operation, progress_callback
                        )
                else:
                    results = []
                
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
        
        orchestrator = ReportingWrapper(orchestrator, config.report_dir)
    
    return orchestrator


def scan_drama_directories(config: ProcessingConfig) -> List[Path]:
    """扫描短剧目录
    
    Args:
        config: 处理配置对象
        
    Returns:
        短剧目录路径列表
    """
    scanner = DirectoryScanner()
    
    # 检查 drama_root 是否是单个短剧目录还是包含多个短剧的根目录
    drama_root = config.drama_root
    
    # 如果 drama_root 本身符合 drama-XXXX 模式，直接返回
    if drama_root.name.startswith('drama-'):
        return [drama_root]
    
    # 否则扫描子目录
    drama_dirs = scanner.scan_drama_root(drama_root)
    return [d.path for d in drama_dirs]


def run_merge(config: ProcessingConfig) -> bool:
    """执行视频合并
    
    Args:
        config: 处理配置对象
        
    Returns:
        是否成功（所有任务都成功返回 True）
    """
    try:
        # 创建编排器
        orchestrator = create_orchestrator(config)
        
        # 创建进度跟踪器
        progress_tracker = ProgressTracker(show_progress=True)
        
        # 扫描短剧目录
        drama_dirs = scan_drama_directories(config)
        
        if not drama_dirs:
            orchestrator.logger.logger.warning(f"未找到任何短剧目录: {config.drama_root}")
            return False
        
        orchestrator.logger.logger.info(f"找到 {len(drama_dirs)} 个短剧目录")
        
        # 批量处理
        skip_completed = config.enable_resume
        results = orchestrator.process_batch(
            drama_dirs,
            operation="merge",
            progress_callback=progress_tracker,
            skip_completed=skip_completed
        )
        
        # 检查结果
        success_count = sum(1 for r in results if r.status == ProcessingStatus.COMPLETED)
        total_count = len(results)
        
        orchestrator.logger.logger.info(f"合并完成: {success_count}/{total_count} 成功")
        
        return success_count == total_count
        
    except Exception as e:
        print(f"执行合并时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_separate(config: ProcessingConfig) -> bool:
    """执行音频分离
    
    Args:
        config: 处理配置对象
        
    Returns:
        是否成功（所有任务都成功返回 True）
    """
    try:
        # 创建编排器
        orchestrator = create_orchestrator(config)
        
        # 创建进度跟踪器
        progress_tracker = ProgressTracker(show_progress=True)
        
        # 扫描短剧目录
        drama_dirs = scan_drama_directories(config)
        
        if not drama_dirs:
            orchestrator.logger.logger.warning(f"未找到任何短剧目录: {config.drama_root}")
            return False
        
        orchestrator.logger.logger.info(f"找到 {len(drama_dirs)} 个短剧目录")
        
        # 批量处理
        skip_completed = config.enable_resume
        results = orchestrator.process_batch(
            drama_dirs,
            operation="separate",
            progress_callback=progress_tracker,
            skip_completed=skip_completed
        )
        
        # 检查结果
        success_count = sum(1 for r in results if r.status == ProcessingStatus.COMPLETED)
        total_count = len(results)
        
        orchestrator.logger.logger.info(f"音频分离完成: {success_count}/{total_count} 成功")
        
        return success_count == total_count
        
    except Exception as e:
        print(f"执行音频分离时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_transcode(config: ProcessingConfig) -> bool:
    """执行视频转码
    
    Args:
        config: 处理配置对象
        
    Returns:
        是否成功（所有任务都成功返回 True）
    """
    try:
        # 创建编排器
        orchestrator = create_orchestrator(config)
        
        # 创建进度跟踪器
        progress_tracker = ProgressTracker(show_progress=True)
        
        # 扫描短剧目录
        drama_dirs = scan_drama_directories(config)
        
        if not drama_dirs:
            orchestrator.logger.logger.warning(f"未找到任何短剧目录: {config.drama_root}")
            return False
        
        orchestrator.logger.logger.info(f"找到 {len(drama_dirs)} 个短剧目录")
        
        # 批量处理
        skip_completed = config.enable_resume
        results = orchestrator.process_batch(
            drama_dirs,
            operation="transcode",
            progress_callback=progress_tracker,
            skip_completed=skip_completed
        )
        
        # 检查结果
        success_count = sum(1 for r in results if r.status == ProcessingStatus.COMPLETED)
        total_count = len(results)
        
        orchestrator.logger.logger.info(f"转码完成: {success_count}/{total_count} 成功")
        
        return success_count == total_count
        
    except Exception as e:
        print(f"执行转码时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
