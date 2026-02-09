"""
核心数据类和枚举定义

本模块定义了短剧视频批量处理工具的核心数据结构，包括：
- 处理状态枚举
- 字幕格式枚举
- 各种数据类（处理结果、进度信息、视频片段等）
- 配置类
"""

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


class ProcessingStatus(Enum):
    """处理状态枚举
    
    用于表示任务的当前处理状态。
    
    Attributes:
        PENDING: 等待处理
        IN_PROGRESS: 正在处理
        COMPLETED: 处理完成
        FAILED: 处理失败
        SKIPPED: 已跳过
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SubtitleFormat(Enum):
    """字幕格式枚举
    
    支持的字幕文件格式。
    
    Attributes:
        SRT: SubRip 字幕格式 (.srt)
        ASS: Advanced SubStation Alpha 字幕格式 (.ass)
    """
    SRT = "srt"
    ASS = "ass"


@dataclass
class ProcessingResult:
    """处理结果
    
    表示单个处理任务的结果。
    
    Attributes:
        status: 处理状态
        input_path: 输入文件/目录路径
        output_path: 输出文件/目录路径（如果成功）
        error_message: 错误信息（如果失败）
        duration_seconds: 处理耗时（秒）
    """
    status: ProcessingStatus
    input_path: Path
    output_path: Optional[Path]
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class ProgressInfo:
    """进度信息
    
    表示批量处理任务的进度。
    
    Attributes:
        current: 当前已处理的任务数
        total: 总任务数
        current_file: 当前正在处理的文件名
        percentage: 完成百分比 (0-100)
    """
    current: int
    total: int
    current_file: str
    percentage: float


@dataclass
class VideoSegment:
    """视频片段
    
    表示一个视频片段文件的信息。
    
    Attributes:
        path: 视频文件路径
        duration_seconds: 视频时长（秒）
        index: 片段序号
    """
    path: Path
    duration_seconds: float
    index: int


@dataclass
class SubtitleSegment:
    """字幕片段
    
    表示一个字幕文件的信息。
    
    Attributes:
        path: 字幕文件路径
        index: 片段序号
        format: 字幕格式
    """
    path: Path
    index: int
    format: SubtitleFormat


@dataclass
class SubtitleEntry:
    """字幕条目
    
    表示单个字幕条目（一条字幕）。
    
    Attributes:
        index: 字幕序号
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        text: 字幕文本
        style: 样式信息（ASS 格式使用）
    """
    index: int
    start_time: float  # 秒
    end_time: float    # 秒
    text: str
    style: Optional[str] = None  # ASS 格式的样式信息
    
    def shift_time(self, offset_seconds: float) -> 'SubtitleEntry':
        """偏移时间戳
        
        创建一个新的字幕条目，时间戳偏移指定的秒数。
        
        Args:
            offset_seconds: 偏移量（秒），正数向后偏移，负数向前偏移
            
        Returns:
            新的 SubtitleEntry 实例，时间戳已偏移
        """
        return SubtitleEntry(
            index=self.index,
            start_time=self.start_time + offset_seconds,
            end_time=self.end_time + offset_seconds,
            text=self.text,
            style=self.style
        )


@dataclass
class DramaDirectory:
    """短剧目录
    
    表示一个短剧目录的结构信息。
    
    Attributes:
        path: 目录路径
        name: 目录名称
        has_video_dir: 是否存在 video/ 子目录
        has_srt_dir: 是否存在 srt/ 子目录
        has_merged_dir: 是否存在 merged/ 子目录
        has_cleared_dir: 是否存在 cleared/ 子目录
    """
    path: Path
    name: str
    has_video_dir: bool
    has_srt_dir: bool
    has_merged_dir: bool
    has_cleared_dir: bool


@dataclass
class TranscodeSpec:
    """转码规格
    
    定义视频转码的目标规格。
    
    Attributes:
        width: 目标宽度（像素）
        height: 目标高度（像素）
        video_codec: 视频编码器（默认 libx264）
        audio_codec: 音频编码器（默认 aac）
    """
    width: int
    height: int
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    
    @property
    def resolution_name(self) -> str:
        """分辨率名称
        
        Returns:
            分辨率名称，如 "1080p"、"720p"
        """
        return f"{self.height}p"


@dataclass
class ProcessingConfig:
    """处理配置
    
    系统的全局配置选项。
    
    Attributes:
        drama_root: 短剧根目录路径
        max_workers: 最大并发处理数量
        enable_resume: 是否启用断点续传
        state_file: 状态文件路径
        audio_separator_model: 音频分离模型
        accompaniment_volume: 伴奏保留音量（0.0-1.0）
        transcode_specs: 转码规格列表
        preserve_aspect_ratio: 是否保持宽高比
        overwrite_existing: 是否覆盖已存在的文件
        add_numeric_suffix: 是否添加数字后缀避免覆盖
        generate_report: 是否生成处理报告
        report_dir: 报告输出目录
        log_level: 日志级别
        log_file: 日志文件路径
    """
    drama_root: Path
    max_workers: int = 4
    enable_resume: bool = True
    state_file: Optional[Path] = None
    audio_separator_model: str = "spleeter:2stems"
    accompaniment_volume: float = 0.0
    transcode_specs: Optional[List[TranscodeSpec]] = None
    preserve_aspect_ratio: bool = True
    overwrite_existing: bool = False
    add_numeric_suffix: bool = True
    generate_report: bool = True
    report_dir: Optional[Path] = None
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    def __post_init__(self):
        """初始化后处理，设置默认值"""
        if self.state_file is None:
            self.state_file = Path(".drama_processor_state.json")
        if self.report_dir is None:
            self.report_dir = Path("reports")
        if self.transcode_specs is None:
            self.transcode_specs = [
                TranscodeSpec(1920, 1080),  # 1080p
                TranscodeSpec(1280, 720),   # 720p
                TranscodeSpec(854, 480),    # 480p
            ]
