"""
短剧视频批量处理工具

提供三个独立的视频处理功能模块：
1. 视频合并模块：将多个视频片段和字幕文件合并为完整的视频和字幕
2. 音频分离模块：去除背景音乐，保留人声对话
3. 视频转码模块：生成多种分辨率和格式的视频文件
"""

__version__ = "0.1.0"
__author__ = "Drama Processor Team"

from .models import (
    ProcessingStatus,
    SubtitleFormat,
    ProcessingResult,
    ProgressInfo,
    VideoSegment,
    SubtitleSegment,
    SubtitleEntry,
    DramaDirectory,
    TranscodeSpec,
    ProcessingConfig,
)

from .interfaces import (
    ProgressCallback,
    VideoProcessor,
)

from .resource_monitor import (
    ResourceMonitor,
    ResourceUsage,
)

__all__ = [
    # 枚举
    "ProcessingStatus",
    "SubtitleFormat",
    # 数据类
    "ProcessingResult",
    "ProgressInfo",
    "VideoSegment",
    "SubtitleSegment",
    "SubtitleEntry",
    "DramaDirectory",
    "TranscodeSpec",
    "ProcessingConfig",
    "ResourceUsage",
    # 接口
    "ProgressCallback",
    "VideoProcessor",
    # 资源监控
    "ResourceMonitor",
]
