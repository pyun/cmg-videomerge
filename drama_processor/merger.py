"""
视频合并模块

将多个视频片段和字幕文件合并为完整的视频和字幕。

验证需求：1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
"""

import time
from pathlib import Path
from typing import List, Optional

from .interfaces import VideoProcessor, ProgressCallback
from .models import (
    ProcessingResult,
    ProcessingStatus,
    VideoSegment,
    SubtitleSegment,
    SubtitleFormat,
    ProgressInfo,
)
from .sorter import FileSorter
from .ffmpeg_wrapper import FFmpegWrapper, OptimizedFFmpegWrapper
from .subtitle import SubtitleFile
from .logger import ProcessingLogger
from .file_manager import FileManager


class VideoMerger(VideoProcessor):
    """视频合并器
    
    将 video/ 目录下的视频片段和 srt/ 目录下的字幕文件
    合并为单个视频和字幕文件，输出到 merged/ 目录。
    
    验证需求：1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
    """
    
    def __init__(self, use_optimized_ffmpeg: bool = True):
        """初始化视频合并器
        
        Args:
            use_optimized_ffmpeg: 是否使用优化的 FFmpeg 包装器（默认 True）
        """
        if use_optimized_ffmpeg:
            self.ffmpeg = OptimizedFFmpegWrapper(enable_gpu=False, preset="medium")
        else:
            self.ffmpeg = FFmpegWrapper()
        
        self.file_manager = FileManager()
        self.logger = ProcessingLogger()
    
    def scan_video_segments(self, video_dir: Path) -> List[VideoSegment]:
        """扫描并排序视频片段
        
        扫描 video/ 目录下的所有 .mp4 文件，按文件名自然排序，
        并获取每个视频的时长信息。
        
        Args:
            video_dir: video/ 目录路径
            
        Returns:
            排序后的视频片段列表
            
        Raises:
            FileNotFoundError: 如果目录不存在
            ValueError: 如果没有找到视频文件
            
        验证需求：1.1, 1.2, 5.5
        """
        if not video_dir.exists():
            raise FileNotFoundError(f"视频目录不存在: {video_dir}")
        
        # 扫描所有 .mp4 文件
        video_files = list(video_dir.glob("*.mp4"))
        
        if not video_files:
            raise ValueError(f"未找到视频文件: {video_dir}")
        
        # 使用自然排序
        sorted_files = FileSorter.sort_files(video_files)
        
        # 验证序列连续性
        is_valid, error_msg = FileSorter.validate_sequence(sorted_files)
        if not is_valid:
            self.logger.logger.warning(f"视频序列验证失败: {error_msg}")
        
        # 创建 VideoSegment 对象列表
        segments = []
        for idx, video_path in enumerate(sorted_files, start=1):
            try:
                # 获取视频时长
                duration = self.ffmpeg.get_video_duration(video_path)
                
                segments.append(VideoSegment(
                    path=video_path,
                    duration_seconds=duration,
                    index=idx
                ))
            except Exception as e:
                self.logger.logger.error(f"获取视频信息失败: {video_path} - {str(e)}")
                raise
        
        return segments
    
    def scan_subtitle_segments(self, srt_dir: Path) -> List[SubtitleSegment]:
        """扫描并排序字幕片段（支持 SRT 和 ASS 格式）
        
        扫描 srt/ 目录下的所有 .srt 和 .ass 文件，按文件名自然排序。
        
        Args:
            srt_dir: srt/ 目录路径
            
        Returns:
            排序后的字幕片段列表（如果没有字幕文件则返回空列表）
            
        验证需求：1.3, 5.6
        """
        if not srt_dir.exists():
            self.logger.logger.warning(f"字幕目录不存在: {srt_dir}")
            return []
        
        # 扫描所有字幕文件（.srt 和 .ass）
        subtitle_files = list(srt_dir.glob("*.srt")) + list(srt_dir.glob("*.ass"))
        
        if not subtitle_files:
            self.logger.logger.warning(f"未找到字幕文件: {srt_dir}")
            return []
        
        # 使用自然排序
        sorted_files = FileSorter.sort_files(subtitle_files)
        
        # 验证序列连续性
        is_valid, error_msg = FileSorter.validate_sequence(sorted_files)
        if not is_valid:
            self.logger.logger.warning(f"字幕序列验证失败: {error_msg}")
        
        # 创建 SubtitleSegment 对象列表
        segments = []
        for idx, subtitle_path in enumerate(sorted_files, start=1):
            # 检测字幕格式
            ext = subtitle_path.suffix.lower()
            if ext == '.srt':
                format = SubtitleFormat.SRT
            elif ext == '.ass':
                format = SubtitleFormat.ASS
            else:
                self.logger.logger.warning(f"不支持的字幕格式: {subtitle_path}")
                continue
            
            segments.append(SubtitleSegment(
                path=subtitle_path,
                index=idx,
                format=format
            ))
        
        return segments
    
    def merge_videos(
        self, 
        segments: List[VideoSegment], 
        output_path: Path
    ) -> None:
        """合并视频片段
        
        使用 FFmpeg 将多个视频片段合并为一个完整的视频文件。
        使用 concat demuxer 进行快速合并（不重新编码）。
        
        Args:
            segments: 视频片段列表
            output_path: 输出文件路径
            
        Raises:
            ValueError: 如果片段列表为空
            FFmpegError: 如果 FFmpeg 执行失败
            
        验证需求：1.4, 1.6
        """
        if not segments:
            raise ValueError("视频片段列表为空")
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果只有一个片段，直接复制
        if len(segments) == 1:
            import shutil
            shutil.copy2(segments[0].path, output_path)
            self.logger.logger.info(f"只有一个视频片段，直接复制: {output_path}")
            return
        
        # 使用优化的合并命令（如果可用）
        if isinstance(self.ffmpeg, OptimizedFFmpegWrapper):
            segment_paths = [seg.path for seg in segments]
            cmd = self.ffmpeg.build_merge_command(segment_paths, output_path)
            
            # 执行命令
            import subprocess
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    check=True
                )
                self.logger.logger.info(f"视频合并成功: {output_path}")
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr if e.stderr else str(e)
                self.logger.logger.error(f"视频合并失败: {error_msg}")
                raise Exception(f"视频合并失败: {error_msg}")
            finally:
                # 清理临时的 concat 列表文件
                concat_file = output_path.parent / 'concat_list.txt'
                if concat_file.exists():
                    concat_file.unlink()
        else:
            # 使用标准的 FFmpeg 包装器
            from .ffmpeg_wrapper import FFmpegCommand
            
            # 构建 concat filter 命令
            segment_paths = [seg.path for seg in segments]
            
            # 创建临时的 concat 列表文件
            concat_file = output_path.parent / 'concat_list.txt'
            with open(concat_file, 'w', encoding='utf-8') as f:
                for seg_path in segment_paths:
                    f.write(f"file '{seg_path.absolute()}'\n")
            
            try:
                command = FFmpegCommand(
                    inputs=[concat_file],
                    output=output_path,
                    options=['-f', 'concat', '-safe', '0', '-c', 'copy', '-y']
                )
                
                self.ffmpeg.execute(command)
                self.logger.logger.info(f"视频合并成功: {output_path}")
            finally:
                # 清理临时文件
                if concat_file.exists():
                    concat_file.unlink()
    
    def merge_subtitles(
        self, 
        segments: List[SubtitleSegment],
        video_segments: List[VideoSegment],
        output_path: Path
    ) -> None:
        """合并字幕文件并调整时间戳（自动检测格式）
        
        将多个字幕文件合并为一个完整的字幕文件，根据视频片段的时长
        自动调整每个字幕文件的时间戳偏移。
        
        Args:
            segments: 字幕片段列表
            video_segments: 对应的视频片段列表（用于计算时间偏移）
            output_path: 输出文件路径
            
        Raises:
            ValueError: 如果片段列表为空或格式不一致
            
        验证需求：1.5, 1.7
        """
        if not segments:
            raise ValueError("字幕片段列表为空")
        
        # 检查所有字幕文件格式是否一致
        first_format = segments[0].format
        for seg in segments[1:]:
            if seg.format != first_format:
                raise ValueError(
                    f"字幕格式不一致: {first_format.value} vs {seg.format.value}"
                )
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果只有一个字幕文件，直接复制
        if len(segments) == 1:
            import shutil
            shutil.copy2(segments[0].path, output_path)
            self.logger.logger.info(f"只有一个字幕文件，直接复制: {output_path}")
            return
        
        # 合并字幕文件
        all_entries = []
        cumulative_offset = 0.0
        global_index = 1
        
        # 获取第一个字幕文件的解析器（用于保存）
        first_subtitle = SubtitleFile.parse(segments[0].path)
        parser = first_subtitle.parser
        
        for i, subtitle_seg in enumerate(segments):
            # 解析字幕文件
            subtitle_file = SubtitleFile.parse(subtitle_seg.path)
            
            # 偏移时间戳
            if cumulative_offset > 0:
                subtitle_file = subtitle_file.shift_all(cumulative_offset)
            
            # 重新编号并添加到总列表
            for entry in subtitle_file.entries:
                entry.index = global_index
                all_entries.append(entry)
                global_index += 1
            
            # 累加时间偏移（使用对应视频片段的时长）
            if i < len(video_segments):
                cumulative_offset += video_segments[i].duration_seconds
        
        # 创建合并后的字幕文件
        merged_subtitle = SubtitleFile(
            entries=all_entries,
            format=first_format,
            parser=parser
        )
        
        # 保存合并后的字幕文件
        merged_subtitle.save(output_path)
        self.logger.logger.info(f"字幕合并成功: {output_path}")
    
    def detect_subtitle_format(self, srt_dir: Path) -> Optional[SubtitleFormat]:
        """检测字幕格式（返回第一个找到的格式）
        
        扫描 srt/ 目录，返回第一个找到的字幕文件格式。
        
        Args:
            srt_dir: srt/ 目录路径
            
        Returns:
            检测到的字幕格式，如果没有字幕文件则返回 None
            
        验证需求：1.3
        """
        if not srt_dir.exists():
            return None
        
        # 优先检查 .srt 文件
        srt_files = list(srt_dir.glob("*.srt"))
        if srt_files:
            return SubtitleFormat.SRT
        
        # 检查 .ass 文件
        ass_files = list(srt_dir.glob("*.ass"))
        if ass_files:
            return SubtitleFormat.ASS
        
        return None
    
    def process(
        self, 
        drama_dir: Path, 
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """处理单个短剧目录
        
        完整的处理流程：
        1. 验证目录结构
        2. 扫描视频片段
        3. 扫描字幕片段（可选）
        4. 合并视频
        5. 合并字幕（如果有）
        
        Args:
            drama_dir: 短剧目录路径
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果对象
            
        验证需求：1.1-1.10
        """
        start_time = time.time()
        
        # 通知开始处理
        if progress_callback:
            progress_callback.on_file_start(str(drama_dir))
        
        self.logger.log_task_start("merge", drama_dir)
        
        try:
            # 验证目录结构 - 支持两种目录结构：
            # 1. drama_dir/video 和 drama_dir/srt（旧格式）
            # 2. drama_dir/original/video 和 drama_dir/original/srt（新格式）
            
            # 首先尝试 original/ 子目录（新格式）
            original_dir = drama_dir / "original"
            if original_dir.exists():
                video_dir = original_dir / "video"
                srt_dir = original_dir / "srt"
            else:
                # 回退到直接子目录（旧格式）
                video_dir = drama_dir / "video"
                srt_dir = drama_dir / "srt"
            
            merged_dir = drama_dir / "merged"
            
            if not video_dir.exists():
                error_msg = f"视频目录不存在: {video_dir}"
                self.logger.log_validation_error(drama_dir, error_msg)
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    input_path=drama_dir,
                    output_path=None,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time
                )
            
            # 扫描视频片段
            try:
                video_segments = self.scan_video_segments(video_dir)
            except Exception as e:
                error_msg = f"扫描视频片段失败: {str(e)}"
                self.logger.log_task_error("merge", drama_dir, e)
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    input_path=drama_dir,
                    output_path=None,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time
                )
            
            # 扫描字幕片段（可选）
            subtitle_segments = self.scan_subtitle_segments(srt_dir)
            
            # 创建输出目录
            merged_dir.mkdir(parents=True, exist_ok=True)
            
            # 合并视频 - 使用唯一路径避免覆盖
            merged_video_path = self.file_manager.get_unique_path(merged_dir / "merged.mp4")
            try:
                self.merge_videos(video_segments, merged_video_path)
            except Exception as e:
                error_msg = f"合并视频失败: {str(e)}"
                self.logger.log_task_error("merge", drama_dir, e)
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    input_path=drama_dir,
                    output_path=None,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time
                )
            
            # 合并字幕（如果有）- 使用唯一路径避免覆盖
            if subtitle_segments:
                # 检测字幕格式
                subtitle_format = subtitle_segments[0].format
                subtitle_ext = ".srt" if subtitle_format == SubtitleFormat.SRT else ".ass"
                merged_subtitle_path = self.file_manager.get_unique_path(
                    merged_dir / f"merged{subtitle_ext}"
                )
                
                try:
                    self.merge_subtitles(
                        subtitle_segments,
                        video_segments,
                        merged_subtitle_path
                    )
                except Exception as e:
                    # 字幕合并失败不影响整体成功
                    self.logger.logger.warning(
                        f"字幕合并失败（视频已成功合并）: {str(e)}"
                    )
            else:
                self.logger.logger.info(f"未找到字幕文件，仅合并视频: {drama_dir}")
            
            # 处理完成
            duration = time.time() - start_time
            self.logger.log_task_complete("merge", drama_dir, duration)
            
            result = ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                input_path=drama_dir,
                output_path=merged_dir,
                duration_seconds=duration
            )
            
            if progress_callback:
                progress_callback.on_file_complete(result)
            
            return result
            
        except Exception as e:
            # 未预期的错误
            duration = time.time() - start_time
            error_msg = f"处理失败: {str(e)}"
            self.logger.log_task_error("merge", drama_dir, e)
            
            result = ProcessingResult(
                status=ProcessingStatus.FAILED,
                input_path=drama_dir,
                output_path=None,
                error_message=error_msg,
                duration_seconds=duration
            )
            
            if progress_callback:
                progress_callback.on_file_complete(result)
            
            return result
    
    def process_batch(
        self, 
        drama_dirs: List[Path],
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ProcessingResult]:
        """批量处理多个短剧目录
        
        依次处理每个短剧目录，即使某些目录处理失败，
        也会继续处理剩余的目录。
        
        Args:
            drama_dirs: 短剧目录路径列表
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果列表，与输入目录一一对应
            
        验证需求：1.8, 4.6
        """
        results = []
        total = len(drama_dirs)
        
        for i, drama_dir in enumerate(drama_dirs, start=1):
            # 更新进度
            if progress_callback:
                progress_callback.on_progress(ProgressInfo(
                    current=i,
                    total=total,
                    current_file=str(drama_dir),
                    percentage=(i / total) * 100
                ))
            
            # 处理单个目录
            result = self.process(drama_dir, progress_callback)
            results.append(result)
        
        # 记录批量处理摘要
        success_count = sum(1 for r in results if r.status == ProcessingStatus.COMPLETED)
        failed_count = sum(1 for r in results if r.status == ProcessingStatus.FAILED)
        self.logger.log_batch_summary(total, success_count, failed_count)
        
        return results
