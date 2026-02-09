"""
视频转码模块

生成多种分辨率和格式的视频文件。
"""

import time
from pathlib import Path
from typing import List, Optional, Tuple

from .interfaces import VideoProcessor, ProgressCallback
from .models import ProcessingResult, ProcessingStatus, TranscodeSpec
from .ffmpeg_wrapper import FFmpegWrapper, FFmpegError, OptimizedFFmpegWrapper
from .logger import ProcessingLogger
from .file_manager import FileManager


class VideoTranscoder(VideoProcessor):
    """视频转码器
    
    从 cleared/ 目录读取视频，转码为多种分辨率，
    输出到 encoded/ 目录。
    """
    
    # 预设转码规格
    PRESET_SPECS = [
        TranscodeSpec(1920, 1080),  # 1080p
        TranscodeSpec(1280, 720),   # 720p
        TranscodeSpec(854, 480),    # 480p
    ]
    
    def __init__(
        self,
        specs: Optional[List[TranscodeSpec]] = None,
        enable_gpu: bool = False,
        preset: str = "medium",
        logger: Optional[ProcessingLogger] = None
    ):
        """初始化视频转码器
        
        Args:
            specs: 转码规格列表，默认使用 PRESET_SPECS
            enable_gpu: 是否启用 GPU 加速
            preset: 编码预设（ultrafast, fast, medium, slow 等）
            logger: 日志记录器
        """
        self.specs = specs if specs is not None else self.PRESET_SPECS
        self.ffmpeg = OptimizedFFmpegWrapper(enable_gpu=enable_gpu, preset=preset)
        self.file_manager = FileManager()
        self.logger = logger or ProcessingLogger()
    
    def get_video_resolution(self, video_path: Path) -> Tuple[int, int]:
        """获取视频分辨率
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            (width, height) 视频宽度和高度
            
        Raises:
            FFmpegError: 当无法获取视频信息时
        """
        info = self.ffmpeg.get_video_info(video_path)
        return (info['width'], info['height'])
    
    def transcode(
        self, 
        input_path: Path, 
        output_path: Path, 
        spec: TranscodeSpec,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        """转码视频
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            spec: 转码规格
            progress_callback: 可选的进度回调对象
            
        Raises:
            FFmpegError: 当转码失败时
        """
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 构建转码命令
        cmd = self.ffmpeg.build_transcode_command(input_path, output_path, spec)
        
        # 执行转码
        from .ffmpeg_wrapper import FFmpegCommand
        ffmpeg_cmd = FFmpegCommand(
            inputs=[input_path],
            output=output_path,
            options=cmd[3:]  # 跳过 'ffmpeg -i input_path' 部分
        )
        
        # 定义进度回调
        def on_progress(percentage: float):
            if progress_callback:
                # 这里可以更新进度信息
                pass
        
        self.ffmpeg.execute(ffmpeg_cmd, progress_callback=on_progress)
    
    def should_skip_spec(
        self, 
        input_resolution: Tuple[int, int], 
        target_spec: TranscodeSpec
    ) -> bool:
        """判断是否应该跳过该规格
        
        如果输入视频分辨率低于目标分辨率，则跳过。
        
        Args:
            input_resolution: 输入视频分辨率 (width, height)
            target_spec: 目标转码规格
            
        Returns:
            是否应该跳过
        """
        input_width, input_height = input_resolution
        
        # 如果输入分辨率的高度低于目标分辨率的高度，则跳过
        # 这样可以避免将低分辨率视频放大到高分辨率
        return input_height < target_spec.height
    
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
        start_time = time.time()
        
        try:
            # 检查 cleared/ 目录是否存在
            cleared_dir = drama_dir / "cleared"
            if not cleared_dir.exists():
                error_msg = f"cleared/ 目录不存在: {cleared_dir}"
                self.logger.log_validation_error(drama_dir, error_msg)
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    input_path=drama_dir,
                    output_path=None,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time
                )
            
            # 查找视频文件
            video_files = list(cleared_dir.glob("*.mp4"))
            if not video_files:
                error_msg = f"cleared/ 目录中没有找到视频文件: {cleared_dir}"
                self.logger.log_validation_error(drama_dir, error_msg)
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    input_path=drama_dir,
                    output_path=None,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time
                )
            
            # 使用第一个视频文件
            input_video = video_files[0]
            
            # 获取输入视频分辨率
            input_resolution = self.get_video_resolution(input_video)
            self.logger.logger.info(
                f"输入视频分辨率: {input_resolution[0]}x{input_resolution[1]}"
            )
            
            # 创建 encoded/ 目录
            encoded_dir = drama_dir / "encoded"
            encoded_dir.mkdir(parents=True, exist_ok=True)
            
            # 对每个规格进行转码
            output_files = []
            skipped_specs = []
            
            for spec in self.specs:
                # 检查是否应该跳过该规格
                if self.should_skip_spec(input_resolution, spec):
                    skipped_specs.append(spec.resolution_name)
                    self.logger.logger.warning(
                        f"跳过 {spec.resolution_name} 规格 "
                        f"(输入分辨率 {input_resolution[1]}p 低于目标分辨率)"
                    )
                    continue
                
                # 生成输出文件名 - 使用唯一路径避免覆盖
                output_filename = f"{input_video.stem}_{spec.resolution_name}.mp4"
                output_path = self.file_manager.get_unique_path(encoded_dir / output_filename)
                
                self.logger.logger.info(
                    f"开始转码到 {spec.resolution_name}: {output_path}"
                )
                
                # 执行转码
                self.transcode(input_video, output_path, spec, progress_callback)
                output_files.append(output_path)
                
                self.logger.logger.info(
                    f"完成转码到 {spec.resolution_name}: {output_path}"
                )
            
            # 复制字幕文件（如果存在）- 使用唯一路径避免覆盖
            subtitle_files = list(cleared_dir.glob("*.srt")) + list(cleared_dir.glob("*.ass"))
            for subtitle_file in subtitle_files:
                dest_path = self.file_manager.get_unique_path(encoded_dir / subtitle_file.name)
                self.file_manager.copy_file(subtitle_file, dest_path)
                self.logger.logger.info(f"复制字幕文件: {subtitle_file.name}")
            
            # 记录跳过的规格
            if skipped_specs:
                self.logger.logger.info(
                    f"跳过的规格: {', '.join(skipped_specs)}"
                )
            
            duration = time.time() - start_time
            self.logger.log_task_complete("转码", drama_dir, duration)
            
            return ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                input_path=drama_dir,
                output_path=encoded_dir,
                error_message=None,
                duration_seconds=duration
            )
            
        except FFmpegError as e:
            duration = time.time() - start_time
            error_msg = f"FFmpeg 错误: {str(e)}"
            self.logger.log_task_error("转码", drama_dir, e)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                input_path=drama_dir,
                output_path=None,
                error_message=error_msg,
                duration_seconds=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"转码失败: {str(e)}"
            self.logger.log_task_error("转码", drama_dir, e)
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                input_path=drama_dir,
                output_path=None,
                error_message=error_msg,
                duration_seconds=duration
            )
    
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
            处理结果列表
        """
        results = []
        total = len(drama_dirs)
        
        for i, drama_dir in enumerate(drama_dirs, 1):
            self.logger.logger.info(f"处理 {i}/{total}: {drama_dir}")
            
            if progress_callback:
                progress_callback.on_file_start(str(drama_dir))
            
            result = self.process(drama_dir, progress_callback)
            results.append(result)
            
            if progress_callback:
                progress_callback.on_file_complete(result)
        
        # 记录批量处理摘要
        success_count = sum(1 for r in results if r.status == ProcessingStatus.COMPLETED)
        failed_count = sum(1 for r in results if r.status == ProcessingStatus.FAILED)
        self.logger.log_batch_summary(total, success_count, failed_count)
        
        return results
