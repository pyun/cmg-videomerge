"""
音频分离模块

去除背景音乐，保留人声对话。
"""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

from .interfaces import VideoProcessor, ProgressCallback
from .models import ProcessingResult, ProcessingStatus, ProgressInfo
from .ffmpeg_wrapper import FFmpegWrapper, FFmpegCommand, FFmpegError
from .file_manager import FileManager
from .logger import ProcessingLogger


class AudioSeparationError(Exception):
    """音频分离错误"""
    pass


class AudioSeparator(VideoProcessor):
    """音频分离器
    
    从 merged/ 目录读取视频，分离人声和背景音乐，
    将只保留人声的视频输出到 cleared/ 目录。
    
    支持的音频分离模型：
    - spleeter:2stems (默认) - 人声和伴奏分离
    - spleeter:4stems - 人声、鼓、贝斯、其他
    - spleeter:5stems - 人声、鼓、贝斯、钢琴、其他
    
    Attributes:
        ffmpeg: FFmpeg 包装器实例
        file_manager: 文件管理器实例
        logger: 日志记录器实例
        model: 音频分离模型名称
    """
    
    def __init__(
        self,
        model: str = "spleeter:2stems",
        accompaniment_volume: float = 0.0,
        log_file: Optional[Path] = None,
        log_level: str = "INFO"
    ):
        """初始化音频分离器
        
        Args:
            model: 音频分离模型，可选值：
                  - "spleeter:2stems" (默认) - 人声和伴奏
                  - "spleeter:4stems" - 4轨分离
                  - "spleeter:5stems" - 5轨分离
            accompaniment_volume: 伴奏保留音量（0.0-1.0）
                  - 0.0: 完全去除伴奏（默认）
                  - 0.2: 保留20%伴奏音量（推荐，可保留部分音效）
                  - 0.5: 保留50%伴奏音量
                  - 1.0: 保留100%伴奏音量（相当于不处理）
            log_file: 日志文件路径（可选）
            log_level: 日志级别
        """
        self.ffmpeg = FFmpegWrapper()
        self.file_manager = FileManager()
        self.logger = ProcessingLogger(log_file, log_level)
        self.model = model
        self.accompaniment_volume = max(0.0, min(1.0, accompaniment_volume))  # 限制在0-1之间
        self._separator_checked = False  # 延迟检查标志
    
    def _check_separator_available(self) -> None:
        """检查音频分离工具是否可用
        
        Raises:
            AudioSeparationError: 如果音频分离工具不可用
        """
        try:
            result = subprocess.run(
                ['spleeter', '--help'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                raise AudioSeparationError(
                    "Spleeter 未正确安装。请运行: pip install spleeter==2.3.0"
                )
        except FileNotFoundError:
            raise AudioSeparationError(
                "未找到 Spleeter。请运行: pip install spleeter==2.3.0"
            )
        except subprocess.TimeoutExpired:
            pass
    
    def extract_audio(self, video_path: Path) -> Path:
        """从视频中提取音频
        
        使用 FFmpeg 从视频文件中提取音频轨道，保存为 WAV 格式。
        WAV 格式是无损的，适合后续的音频分离处理。
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            提取的音频文件路径（WAV 格式）
            
        Raises:
            FFmpegError: 当音频提取失败时
        """
        if not video_path.exists():
            raise FFmpegError(f"视频文件不存在: {video_path}")
        
        # 创建临时音频文件
        audio_path = video_path.parent / f"{video_path.stem}_audio.wav"
        
        # 构建 FFmpeg 命令：提取音频为 WAV 格式
        command = FFmpegCommand(
            inputs=[video_path],
            output=audio_path,
            options=[
                '-vn',           # 不处理视频流
                '-acodec', 'pcm_s16le',  # 使用 PCM 16-bit 编码
                '-ar', '44100',  # 采样率 44.1kHz
                '-ac', '2',      # 双声道
                '-y'             # 覆盖输出文件
            ]
        )
        
        self.ffmpeg.execute(command)
        
        return audio_path
    
    def separate_vocals(self, audio_path: Path) -> Tuple[Path, Path]:
        """分离人声和背景音乐
        
        使用 Spleeter 将音频分离为人声和背景音乐两个轨道。
        对于长音频（超过10分钟），会分段处理以降低内存占用。
        
        Args:
            audio_path: 音频文件路径（WAV 格式）
            
        Returns:
            (vocal_path, background_path) 人声和背景音乐的文件路径
            
        Raises:
            AudioSeparationError: 当音频分离失败时
        """
        if not audio_path.exists():
            raise AudioSeparationError(f"音频文件不存在: {audio_path}")
        
        # 获取音频时长
        try:
            duration = self.ffmpeg.get_audio_duration(audio_path)
            self.logger.logger.info(f"音频时长: {duration:.2f}秒")
        except Exception as e:
            self.logger.logger.warning(f"无法获取音频时长: {e}，使用默认处理方式")
            duration = 0
        
        # 创建临时输出目录
        output_dir = audio_path.parent / f"{audio_path.stem}_separated"
        output_dir.mkdir(exist_ok=True)
        
        try:
            # 如果音频超过10分钟（600秒），分段处理以降低内存占用
            if duration > 600:
                self.logger.logger.info(f"音频较长（{duration:.0f}秒），将分段处理以降低内存占用")
                return self._separate_long_audio(audio_path, output_dir, duration)
            else:
                return self._separate_with_spleeter(audio_path, output_dir)
        except Exception as e:
            # 清理临时目录
            if output_dir.exists():
                try:
                    shutil.rmtree(output_dir, ignore_errors=True)
                except:
                    self.logger.logger.warning(f"无法清理临时目录: {output_dir}")
            raise
    
    def _separate_with_spleeter(
        self, 
        audio_path: Path, 
        output_dir: Path
    ) -> Tuple[Path, Path]:
        """使用 Spleeter 分离音频
        
        Args:
            audio_path: 音频文件路径
            output_dir: 输出目录
            
        Returns:
            (vocal_path, background_path)
        """
        # 获取音频时长，用于设置 Spleeter 的 duration 参数
        try:
            audio_duration = self.ffmpeg.get_audio_duration(audio_path)
            # 向上取整，确保处理完整音频
            duration_param = int(audio_duration) + 1
            self.logger.logger.info(f"设置 Spleeter duration={duration_param}")
        except Exception as e:
            self.logger.logger.warning(f"无法获取音频时长: {e}，使用默认 duration")
            duration_param = None
        
        # 运行 Spleeter
        cmd = [
            'spleeter',
            'separate',
            '-p', self.model,
            '-o', str(output_dir),
        ]
        
        # 如果获取到时长，添加 duration 参数
        if duration_param:
            cmd.extend(['-d', str(duration_param)])
        
        cmd.append(str(audio_path))
        
        self.logger.logger.info(f"执行 Spleeter 命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=3600  # 60 分钟超时
            )
            
            # 记录 Spleeter 的输出
            if result.stdout:
                self.logger.logger.debug(f"Spleeter 输出:\n{result.stdout}")
            if result.stderr:
                self.logger.logger.debug(f"Spleeter 错误输出:\n{result.stderr}")
            
            if result.returncode != 0:
                # 返回码 -9 表示被 SIGKILL 终止（通常是内存不足）
                if result.returncode == -9:
                    raise AudioSeparationError(
                        f"Spleeter 被系统终止（可能是内存不足）。"
                        f"建议：1) 增加系统内存或 swap；2) 使用分段处理（音频会自动分段）"
                    )
                raise AudioSeparationError(
                    f"Spleeter 执行失败 (返回码: {result.returncode}):\n{result.stderr}"
                )
        except subprocess.TimeoutExpired:
            raise AudioSeparationError("Spleeter 执行超时（超过 60 分钟）")
        except Exception as e:
            if isinstance(e, AudioSeparationError):
                raise
            raise AudioSeparationError(f"Spleeter 执行错误: {str(e)}")
        
        # Spleeter 输出结构：output_dir/audio_name/vocals.wav 和 accompaniment.wav
        separated_dir = output_dir / audio_path.stem
        vocal_path = separated_dir / 'vocals.wav'
        background_path = separated_dir / 'accompaniment.wav'
        
        if not vocal_path.exists():
            raise AudioSeparationError(f"未找到人声文件: {vocal_path}")
        if not background_path.exists():
            raise AudioSeparationError(f"未找到背景音乐文件: {background_path}")
        
        # 检查输出音频的时长
        try:
            vocal_duration = self.ffmpeg.get_audio_duration(vocal_path)
            input_duration = self.ffmpeg.get_audio_duration(audio_path)
            
            self.logger.logger.info(f"输入音频时长: {input_duration:.2f}秒, 输出人声时长: {vocal_duration:.2f}秒")
            
            # 如果输出音频明显短于输入音频，发出警告
            if vocal_duration < input_duration - 5.0:
                self.logger.logger.error(
                    f"Spleeter 输出音频比输入短 {input_duration - vocal_duration:.2f}秒！"
                )
        except Exception as e:
            self.logger.logger.warning(f"无法验证输出音频时长: {e}")
        
        # 如果需要混合伴奏，创建混合音频
        if self.accompaniment_volume > 0:
            self.logger.logger.info(f"混合人声和伴奏（伴奏音量: {self.accompaniment_volume*100:.0f}%）")
            mixed_path = output_dir / "mixed.wav"
            self._mix_audio(vocal_path, background_path, mixed_path, self.accompaniment_volume)
            return mixed_path, background_path
        
        return vocal_path, background_path
    
    def _separate_long_audio(
        self,
        audio_path: Path,
        output_dir: Path,
        duration: float
    ) -> Tuple[Path, Path]:
        """分段处理长音频
        
        将长音频分成多个片段，分别用 Spleeter 处理，然后合并结果。
        每段8分钟，避免内存占用过大。
        
        Args:
            audio_path: 音频文件路径
            output_dir: 输出目录
            duration: 音频总时长（秒）
            
        Returns:
            (vocal_path, background_path)
        """
        # 每段处理8分钟（480秒）
        segment_duration = 480
        
        segments_dir = output_dir / "segments"
        segments_dir.mkdir(exist_ok=True)
        
        vocal_segments = []
        background_segments = []
        
        # 计算需要分多少段
        num_segments = int((duration + segment_duration - 1) / segment_duration)
        self.logger.logger.info(f"将音频分为 {num_segments} 段处理")
        
        for i in range(num_segments):
            start_time = i * segment_duration
            # 最后一段处理到结尾
            if i == num_segments - 1:
                segment_duration_actual = duration - start_time
            else:
                segment_duration_actual = segment_duration
            
            self.logger.logger.info(
                f"处理第 {i+1}/{num_segments} 段 "
                f"(时间: {start_time:.1f}s - {start_time + segment_duration_actual:.1f}s)"
            )
            
            # 提取音频片段
            segment_path = segments_dir / f"segment_{i:03d}.wav"
            self._extract_audio_segment(audio_path, segment_path, start_time, segment_duration_actual)
            
            # 分离该片段
            segment_output_dir = segments_dir / f"output_{i:03d}"
            segment_output_dir.mkdir(exist_ok=True)
            
            try:
                vocal_seg, bg_seg = self._separate_with_spleeter(segment_path, segment_output_dir)
                
                vocal_segments.append(vocal_seg)
                background_segments.append(bg_seg)
            finally:
                # 删除原始片段以节省空间
                if segment_path.exists():
                    segment_path.unlink()
        
        # 合并所有片段
        self.logger.logger.info("合并所有处理后的片段")
        
        final_vocal = output_dir / "vocals.wav"
        final_background = output_dir / "accompaniment.wav"
        
        self._concat_audio_segments(vocal_segments, final_vocal)
        self._concat_audio_segments(background_segments, final_background)
        
        # 如果需要混合伴奏，创建混合音频
        if self.accompaniment_volume > 0:
            self.logger.logger.info(f"混合人声和伴奏（伴奏音量: {self.accompaniment_volume*100:.0f}%）")
            mixed_audio = output_dir / "mixed.wav"
            self._mix_audio(final_vocal, final_background, mixed_audio, self.accompaniment_volume)
            return mixed_audio, final_background
        
        return final_vocal, final_background
    
    def _extract_audio_segment(
        self,
        input_path: Path,
        output_path: Path,
        start_time: float,
        duration: float
    ) -> None:
        """提取音频片段
        
        Args:
            input_path: 输入音频文件
            output_path: 输出音频文件
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
        """
        command = FFmpegCommand(
            inputs=[input_path],
            output=output_path,
            options=[
                '-ss', str(start_time),
                '-t', str(duration),
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                '-y'
            ]
        )
        self.ffmpeg.execute(command)
    
    def _concat_audio_segments(
        self,
        segments: List[Path],
        output_path: Path
    ) -> None:
        """合并音频片段
        
        Args:
            segments: 音频片段路径列表
            output_path: 输出文件路径
        """
        # 创建 concat 列表文件
        concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
        
        with open(concat_file, 'w', encoding='utf-8') as f:
            for segment in segments:
                f.write(f"file '{segment.absolute()}'\n")
        
        # 使用 FFmpeg concat
        cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c', 'copy', '-y', str(output_path)]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                raise FFmpegError(f"音频合并失败: {result.stderr}")
        finally:
            # 清理 concat 文件
            if concat_file.exists():
                concat_file.unlink()
    
    def _mix_audio(
        self,
        vocal_path: Path,
        background_path: Path,
        output_path: Path,
        bg_volume: float
    ) -> None:
        """混合人声和伴奏音频
        
        使用 FFmpeg 的 amix 滤镜将人声和伴奏混合，
        可以控制伴奏的音量比例。
        
        Args:
            vocal_path: 人声音频文件路径
            background_path: 伴奏音频文件路径
            output_path: 输出混合音频文件路径
            bg_volume: 伴奏音量（0.0-1.0）
        """
        # 构建 FFmpeg 命令
        # 使用 amix 滤镜混合两个音频流
        # [0:a]volume=1.0[v] - 人声保持原音量
        # [1:a]volume={bg_volume}[b] - 伴奏调整音量
        # [v][b]amix=inputs=2:duration=first - 混合两个音频，以第一个音频的时长为准
        command = FFmpegCommand(
            inputs=[vocal_path, background_path],
            output=output_path,
            options=[
                '-filter_complex',
                f'[0:a]volume=1.0[v];[1:a]volume={bg_volume}[b];[v][b]amix=inputs=2:duration=first',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                '-y'
            ]
        )
        
        self.ffmpeg.execute(command)
    
    def replace_audio(
        self, 
        video_path: Path, 
        audio_path: Path, 
        output_path: Path
    ) -> None:
        """替换视频的音频轨道
        
        使用 FFmpeg 将视频的音频轨道替换为新的音频文件。
        保持原视频的所有视频属性（分辨率、编码、帧率等）。
        如果音频比视频短，会用静音填充；如果音频比视频长，会截断音频。
        
        Args:
            video_path: 原视频文件路径
            audio_path: 新音频文件路径
            output_path: 输出视频文件路径
            
        Raises:
            FFmpegError: 当音频替换失败时
        """
        if not video_path.exists():
            raise FFmpegError(f"视频文件不存在: {video_path}")
        if not audio_path.exists():
            raise FFmpegError(f"音频文件不存在: {audio_path}")
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 获取视频和音频的时长
        try:
            video_duration = self.ffmpeg.get_video_duration(video_path)
            audio_duration = self.ffmpeg.get_audio_duration(audio_path)
            
            self.logger.logger.info(f"视频时长: {video_duration:.2f}秒, 音频时长: {audio_duration:.2f}秒")
            
            # 如果音频比视频短超过1秒，发出警告
            if audio_duration < video_duration - 1.0:
                self.logger.logger.warning(
                    f"音频比视频短 {video_duration - audio_duration:.2f}秒，"
                    f"将用静音填充"
                )
        except Exception as e:
            self.logger.logger.warning(f"无法获取时长信息: {e}，继续处理")
            video_duration = None
        
        self.logger.logger.info("正在替换音频轨道，这可能需要几分钟...")
        
        # 构建 FFmpeg 命令：替换音频轨道
        command = FFmpegCommand(
            inputs=[video_path, audio_path],
            output=output_path,
            options=[
                '-map', '0:v',   # 使用第一个输入的视频流
                '-map', '1:a',   # 使用第二个输入的音频流
                '-c:v', 'copy',  # 直接复制视频流（不重新编码，保持原始质量）
                '-c:a', 'aac',   # 音频编码为 AAC
                '-b:a', '192k',  # 音频比特率 192kbps
                '-y'             # 覆盖输出文件
            ]
        )
        
        # 定义进度回调 - 每5%显示一次
        last_reported = [0]  # 使用列表以便在闭包中修改
        def on_progress(percentage: float):
            # 每5%或最后阶段（>95%）都显示
            current = int(percentage / 5) * 5
            if current > last_reported[0] or percentage > 95:
                self.logger.logger.info(f"音频替换进度: {percentage:.1f}%")
                last_reported[0] = current
        
        self.ffmpeg.execute(command, progress_callback=on_progress if video_duration else None)
        
        self.logger.logger.info("音频替换完成")
    
    def process(
        self, 
        drama_dir: Path, 
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessingResult:
        """处理单个短剧目录
        
        处理流程：
        1. 验证 merged/ 目录是否存在
        2. 从 merged/ 目录读取视频文件
        3. 提取音频轨道
        4. 分离人声和背景音乐
        5. 将人声重新合成到视频中
        6. 保存到 cleared/ 目录
        7. 复制字幕文件（如果存在）
        
        Args:
            drama_dir: 短剧目录路径
            progress_callback: 可选的进度回调对象
            
        Returns:
            处理结果对象
        """
        # 首次调用时检查音频分离工具
        if not self._separator_checked:
            self._check_separator_available()
            self._separator_checked = True
        
        start_time = time.time()
        
        # 通知开始处理
        if progress_callback:
            progress_callback.on_file_start(str(drama_dir))
        
        self.logger.log_task_start("音频分离", drama_dir)
        
        try:
            # 1. 验证目录结构
            merged_dir = drama_dir / "merged"
            if not merged_dir.exists():
                error_msg = f"merged/ 目录不存在: {merged_dir}"
                self.logger.log_validation_error(drama_dir, error_msg)
                result = ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    input_path=drama_dir,
                    output_path=None,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time
                )
                if progress_callback:
                    progress_callback.on_file_complete(result)
                return result
            
            # 2. 查找视频文件
            video_files = list(merged_dir.glob("*.mp4"))
            if not video_files:
                error_msg = f"merged/ 目录中没有视频文件: {merged_dir}"
                self.logger.log_validation_error(drama_dir, error_msg)
                result = ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    input_path=drama_dir,
                    output_path=None,
                    error_message=error_msg,
                    duration_seconds=time.time() - start_time
                )
                if progress_callback:
                    progress_callback.on_file_complete(result)
                return result
            
            # 使用第一个视频文件（通常是 merged.mp4）
            input_video = video_files[0]
            
            # 3. 创建 cleared/ 目录
            cleared_dir = drama_dir / "cleared"
            self.file_manager.ensure_directory(cleared_dir)
            
            # 4. 设置输出路径 - 使用唯一路径避免覆盖
            output_video = self.file_manager.get_unique_path(cleared_dir / input_video.name)
            
            # 5. 创建临时目录用于中间文件
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 6. 提取音频
                self.logger.logger.info(f"提取音频: {input_video.name}")
                audio_path = self.extract_audio(input_video)
                
                # 将音频移到临时目录
                temp_audio = temp_path / audio_path.name
                shutil.move(str(audio_path), str(temp_audio))
                audio_path = temp_audio
                
                # 7. 分离人声和背景音乐
                self.logger.logger.info(f"分离人声和背景音乐（模型: {self.model}）")
                vocal_path, _ = self.separate_vocals(audio_path)
                
                # 8. 替换音频轨道
                self.logger.logger.info(f"替换音频轨道: {output_video.name}")
                self.replace_audio(input_video, vocal_path, output_video)
            
            # 9. 复制字幕文件（如果存在）- 使用唯一路径避免覆盖
            for subtitle_ext in ['.srt', '.ass']:
                subtitle_file = merged_dir / f"{input_video.stem}{subtitle_ext}"
                if subtitle_file.exists():
                    output_subtitle = self.file_manager.get_unique_path(
                        cleared_dir / subtitle_file.name
                    )
                    self.file_manager.copy_file(subtitle_file, output_subtitle)
                    self.logger.logger.info(f"复制字幕文件: {subtitle_file.name}")
            
            # 10. 记录成功
            duration = time.time() - start_time
            self.logger.log_task_complete("音频分离", drama_dir, duration)
            
            result = ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                input_path=drama_dir,
                output_path=output_video,
                duration_seconds=duration
            )
            
            if progress_callback:
                progress_callback.on_file_complete(result)
            
            return result
            
        except Exception as e:
            # 记录错误
            duration = time.time() - start_time
            self.logger.log_task_error("音频分离", drama_dir, e)
            
            result = ProcessingResult(
                status=ProcessingStatus.FAILED,
                input_path=drama_dir,
                output_path=None,
                error_message=str(e),
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
        """
        results = []
        total = len(drama_dirs)
        
        for i, drama_dir in enumerate(drama_dirs, 1):
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
