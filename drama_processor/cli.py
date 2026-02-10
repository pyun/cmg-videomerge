"""
命令行接口

提供命令行工具入口。
"""

import click
import sys
from pathlib import Path
from typing import Optional, List, Tuple

from .models import ProcessingConfig, TranscodeSpec
from .config import ConfigManager


def parse_transcode_specs(specs: Tuple[str, ...]) -> List[TranscodeSpec]:
    """解析转码规格参数
    
    Args:
        specs: 规格字符串元组，如 ('1080p', '720p', '480p')
        
    Returns:
        TranscodeSpec 列表
        
    Raises:
        click.BadParameter: 如果规格格式无效
    """
    if not specs:
        # 返回默认规格
        return [
            TranscodeSpec(1920, 1080),  # 1080p
            TranscodeSpec(1280, 720),   # 720p
            TranscodeSpec(854, 480),    # 480p
        ]
    
    # 预定义的规格映射
    spec_map = {
        '1080p': TranscodeSpec(1920, 1080),
        '720p': TranscodeSpec(1280, 720),
        '480p': TranscodeSpec(854, 480),
        '360p': TranscodeSpec(640, 360),
        '240p': TranscodeSpec(426, 240),
    }
    
    result = []
    for spec_str in specs:
        spec_str = spec_str.lower().strip()
        if spec_str in spec_map:
            result.append(spec_map[spec_str])
        else:
            # 尝试解析自定义格式: WIDTHxHEIGHT (如: 1920x1080)
            if 'x' in spec_str:
                try:
                    width_str, height_str = spec_str.split('x')
                    width = int(width_str)
                    height = int(height_str)
                    if width > 0 and height > 0:
                        result.append(TranscodeSpec(width, height))
                    else:
                        raise click.BadParameter(
                            f"无效的转码规格: {spec_str}，宽度和高度必须大于 0"
                        )
                except ValueError:
                    raise click.BadParameter(
                        f"无效的转码规格: {spec_str}，格式应为 '1080p' 或 '1920x1080'"
                    )
            else:
                raise click.BadParameter(
                    f"无效的转码规格: {spec_str}，支持的格式: 1080p, 720p, 480p, 360p, 240p 或 WIDTHxHEIGHT"
                )
    
    return result


def validate_drama_root(ctx, param, value: str) -> Path:
    """验证 drama_root 参数
    
    Args:
        ctx: Click 上下文
        param: 参数对象
        value: 参数值
        
    Returns:
        验证后的 Path 对象
        
    Raises:
        click.BadParameter: 如果路径无效
    """
    path = Path(value)
    
    if not path.exists():
        raise click.BadParameter(f"目录不存在: {value}")
    
    if not path.is_dir():
        raise click.BadParameter(f"不是一个目录: {value}")
    
    return path


def validate_workers(ctx, param, value: int) -> int:
    """验证 workers 参数
    
    Args:
        ctx: Click 上下文
        param: 参数对象
        value: 参数值
        
    Returns:
        验证后的 workers 值
        
    Raises:
        click.BadParameter: 如果值无效
    """
    if value < 1:
        raise click.BadParameter("并发数量必须至少为 1")
    
    if value > 32:
        raise click.BadParameter("并发数量不应超过 32")
    
    return value


def validate_log_level(ctx, param, value: str) -> str:
    """验证日志级别参数
    
    Args:
        ctx: Click 上下文
        param: 参数对象
        value: 参数值
        
    Returns:
        验证后的日志级别
        
    Raises:
        click.BadParameter: 如果值无效
    """
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    value_upper = value.upper()
    
    if value_upper not in valid_levels:
        raise click.BadParameter(
            f"无效的日志级别: {value}，支持的级别: {', '.join(valid_levels)}"
        )
    
    return value_upper


def create_config_from_options(
    drama_root: Path,
    workers: int,
    resume: bool,
    log_level: str,
    log_file: Optional[str],
    state_file: Optional[str],
    report_dir: Optional[str],
    transcode_specs: Optional[List[TranscodeSpec]] = None
) -> ProcessingConfig:
    """从命令行选项创建配置对象
    
    Args:
        drama_root: 短剧根目录
        workers: 并发数量
        resume: 是否启用断点续传
        log_level: 日志级别
        log_file: 日志文件路径
        state_file: 状态文件路径
        report_dir: 报告目录路径
        transcode_specs: 转码规格列表
        
    Returns:
        ProcessingConfig 对象
    """
    config = ProcessingConfig(
        drama_root=drama_root,
        max_workers=workers,
        enable_resume=resume,
        log_level=log_level
    )
    
    if log_file:
        config.log_file = Path(log_file)
    
    if state_file:
        config.state_file = Path(state_file)
    
    if report_dir:
        config.report_dir = Path(report_dir)
    
    if transcode_specs:
        config.transcode_specs = transcode_specs
    
    return config


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """短剧视频批量处理工具
    
    提供视频合并、音频分离、视频转码三个独立功能。
    
    \b
    示例:
      # 合并视频和字幕
      drama-processor merge /path/to/drama
      
      # 分离音频（去除背景音）
      drama-processor separate /path/to/drama
      
      # 转码为多种规格
      drama-processor transcode /path/to/drama --specs 1080p --specs 720p
    """
    pass


@cli.command()
@click.argument('drama_root', type=click.Path(exists=True), callback=validate_drama_root)
@click.option(
    '--workers', '-w',
    default=4,
    type=int,
    callback=validate_workers,
    help='并发处理数量 (默认: 4)'
)
@click.option(
    '--log-level', '-l',
    default='INFO',
    type=str,
    callback=validate_log_level,
    help='日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
)
@click.option(
    '--log-file',
    type=click.Path(),
    help='日志文件路径 (可选)'
)
@click.option(
    '--report-dir',
    type=click.Path(),
    help='报告输出目录 (默认: reports/)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='配置文件路径 (可选，JSON 格式)'
)
def merge(
    drama_root: Path,
    workers: int,
    log_level: str,
    log_file: Optional[str],
    report_dir: Optional[str],
    config: Optional[str]
):
    """合并视频和字幕
    
    将 video/ 目录下的视频片段和 srt/ 目录下的字幕文件
    合并为单个视频和字幕文件，输出到 merged/ 目录。
    
    \b
    需求:
      - video/ 目录包含视频片段 (video-001.mp4, video-002.mp4, ...)
      - srt/ 目录包含字幕文件 (.srt 或 .ass 格式)
    
    \b
    输出:
      - merged/merged.mp4: 合并后的视频
      - merged/merged.srt 或 merged/merged.ass: 合并后的字幕
    
    \b
    示例:
      drama-processor merge /path/to/drama
      drama-processor merge /path/to/drama --workers 8
    """
    try:
        # 如果提供了配置文件，从文件加载配置
        if config:
            processing_config = ConfigManager.load_from_file(Path(config))
            # 命令行参数覆盖配置文件
            processing_config.drama_root = drama_root
            processing_config.max_workers = workers
            processing_config.enable_resume = False
            processing_config.log_level = log_level
        else:
            # 从命令行选项创建配置
            processing_config = create_config_from_options(
                drama_root, workers, False, log_level,
                log_file, None, report_dir
            )
        
        click.echo(f"开始合并视频: {drama_root}")
        click.echo(f"配置: 并发数={workers}")
        
        # 调用实际的合并逻辑
        from .main import run_merge
        success = run_merge(processing_config)
        
        if not success:
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('drama_root', type=click.Path(exists=True), callback=validate_drama_root)
@click.option(
    '--workers', '-w',
    default=4,
    type=int,
    callback=validate_workers,
    help='并发处理数量 (默认: 4)'
)
@click.option(
    '--model', '-m',
    default='spleeter:2stems',
    type=str,
    help='音频分离模型 (默认: spleeter:2stems)'
)
@click.option(
    '--accompaniment-volume', '-a',
    default=0.0,
    type=float,
    help='伴奏保留音量 (0.0-1.0，默认: 0.0 完全去除，0.2 推荐保留部分音效)'
)
@click.option(
    '--log-level', '-l',
    default='INFO',
    type=str,
    callback=validate_log_level,
    help='日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
)
@click.option(
    '--log-file',
    type=click.Path(),
    help='日志文件路径 (可选)'
)
@click.option(
    '--report-dir',
    type=click.Path(),
    help='报告输出目录 (默认: reports/)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='配置文件路径 (可选，JSON 格式)'
)
def separate(
    drama_root: Path,
    workers: int,
    model: str,
    accompaniment_volume: float,
    log_level: str,
    log_file: Optional[str],
    report_dir: Optional[str],
    config: Optional[str]
):
    """分离音频（去除背景音）
    
    从 merged/ 目录读取视频，分离人声和背景音乐，
    将只保留人声的视频输出到 cleared/ 目录。
    
    \b
    需求:
      - merged/ 目录包含合并后的视频文件
    
    \b
    输出:
      - cleared/merged.mp4: 去除背景音后的视频
      - cleared/merged.srt 或 merged.ass: 复制的字幕文件
    
    \b
    伴奏音量控制:
      - 0.0: 完全去除伴奏（默认）
      - 0.2: 保留20%伴奏音量（推荐，可保留碰撞、摔打等音效）
      - 0.5: 保留50%伴奏音量
      - 1.0: 保留100%伴奏音量（相当于不处理）
    
    \b
    示例:
      drama-processor separate /path/to/drama
      drama-processor separate /path/to/drama --model spleeter:2stems
      drama-processor separate /path/to/drama --accompaniment-volume 0.2
    """
    try:
        # 验证伴奏音量参数
        if not 0.0 <= accompaniment_volume <= 1.0:
            raise click.BadParameter("伴奏音量必须在 0.0 到 1.0 之间")
        
        # 如果提供了配置文件，从文件加载配置
        if config:
            processing_config = ConfigManager.load_from_file(Path(config))
            # 命令行参数覆盖配置文件
            processing_config.drama_root = drama_root
            processing_config.max_workers = workers
            processing_config.enable_resume = False
            processing_config.audio_separator_model = model
            processing_config.log_level = log_level
        else:
            # 从命令行选项创建配置
            processing_config = create_config_from_options(
                drama_root, workers, False, log_level,
                log_file, None, report_dir
            )
            processing_config.audio_separator_model = model
        
        # 添加伴奏音量配置
        processing_config.accompaniment_volume = accompaniment_volume
        
        click.echo(f"开始分离音频: {drama_root}")
        click.echo(f"配置: 并发数={workers}, 模型={model}, 伴奏音量={accompaniment_volume*100:.0f}%")
        
        # 调用实际的分离逻辑
        from .main import run_separate
        success = run_separate(processing_config)
        
        if not success:
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('drama_root', type=click.Path(exists=True), callback=validate_drama_root)
@click.option(
    '--workers', '-w',
    default=4,
    type=int,
    callback=validate_workers,
    help='并发处理数量 (默认: 4)'
)
@click.option(
    '--specs', '-s',
    multiple=True,
    help='转码规格 (如: 1080p, 720p, 480p 或 1920x1080)，可多次指定'
)
@click.option(
    '--gpu/--no-gpu',
    default=False,
    help='启用/禁用 GPU 加速编码 (默认: 禁用)'
)
@click.option(
    '--preset',
    default='medium',
    type=click.Choice(['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']),
    help='编码预设，影响速度和质量 (默认: medium)'
)
@click.option(
    '--log-level', '-l',
    default='INFO',
    type=str,
    callback=validate_log_level,
    help='日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
)
@click.option(
    '--log-file',
    type=click.Path(),
    help='日志文件路径 (可选)'
)
@click.option(
    '--report-dir',
    type=click.Path(),
    help='报告输出目录 (默认: reports/)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='配置文件路径 (可选，JSON 格式)'
)
def transcode(
    drama_root: Path,
    workers: int,
    specs: Tuple[str, ...],
    gpu: bool,
    preset: str,
    log_level: str,
    log_file: Optional[str],
    report_dir: Optional[str],
    config: Optional[str]
):
    """转码视频为多种规格
    
    从 cleared/ 目录读取视频，转码为多种分辨率，
    输出到 encoded/ 目录。
    
    \b
    需求:
      - cleared/ 目录包含去除背景音后的视频文件
    
    \b
    输出:
      - encoded/merged_1080p.mp4: 1080p 视频
      - encoded/merged_720p.mp4: 720p 视频
      - encoded/merged_480p.mp4: 480p 视频
      - encoded/merged.srt 或 merged.ass: 复制的字幕文件
    
    \b
    支持的规格:
      - 预定义: 1080p, 720p, 480p, 360p, 240p
      - 自定义: WIDTHxHEIGHT (如: 1920x1080)
    
    \b
    示例:
      drama-processor transcode /path/to/drama
      drama-processor transcode /path/to/drama --specs 1080p --specs 720p
      drama-processor transcode /path/to/drama --specs 1920x1080 --specs 1280x720
    """
    try:
        # 解析转码规格
        transcode_specs = parse_transcode_specs(specs)
        
        # 如果提供了配置文件，从文件加载配置
        if config:
            processing_config = ConfigManager.load_from_file(Path(config))
            # 命令行参数覆盖配置文件
            processing_config.drama_root = drama_root
            processing_config.max_workers = workers
            processing_config.enable_resume = False
            processing_config.transcode_specs = transcode_specs
            processing_config.log_level = log_level
        else:
            # 从命令行选项创建配置
            processing_config = create_config_from_options(
                drama_root, workers, False, log_level,
                log_file, None, report_dir,
                transcode_specs
            )
        
        click.echo(f"开始转码视频: {drama_root}")
        specs_str = ', '.join([spec.resolution_name for spec in transcode_specs])
        gpu_status = "启用" if gpu else "禁用"
        click.echo(f"配置: 并发数={workers}, 规格=[{specs_str}], GPU={gpu_status}, 预设={preset}")
        
        # 调用实际的转码逻辑
        from .main import run_transcode
        success = run_transcode(processing_config, enable_gpu=gpu, preset=preset)
        
        if not success:
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('drama_root', type=click.Path(exists=True), callback=validate_drama_root)
@click.option(
    '--workers', '-w',
    default=4,
    type=int,
    callback=validate_workers,
    help='并发处理数量 (默认: 4)'
)
@click.option(
    '--model', '-m',
    default='spleeter:2stems',
    type=str,
    help='音频分离模型 (默认: spleeter:2stems)'
)
@click.option(
    '--accompaniment-volume', '-a',
    default=0.0,
    type=float,
    help='伴奏保留音量 (0.0-1.0，默认: 0.0 完全去除，0.2 推荐保留部分音效)'
)
@click.option(
    '--specs', '-s',
    multiple=True,
    help='转码规格 (如: 1080p, 720p, 480p 或 1920x1080)，可多次指定'
)
@click.option(
    '--log-level', '-l',
    default='INFO',
    type=str,
    callback=validate_log_level,
    help='日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
)
@click.option(
    '--log-file',
    type=click.Path(),
    help='日志文件路径 (可选)'
)
@click.option(
    '--report-dir',
    type=click.Path(),
    help='报告输出目录 (默认: reports/)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='配置文件路径 (可选，JSON 格式)'
)
def all(
    drama_root: Path,
    workers: int,
    model: str,
    accompaniment_volume: float,
    specs: Tuple[str, ...],
    log_level: str,
    log_file: Optional[str],
    report_dir: Optional[str],
    config: Optional[str]
):
    """一次性执行完整流程（合并 -> 分离 -> 转码）
    
    依次执行视频合并、音频分离、视频转码三个步骤。
    
    \b
    需求:
      - video/ 目录包含视频片段
      - srt/ 目录包含字幕文件
    
    \b
    输出:
      - merged/merged.mp4: 合并后的视频
      - cleared/merged.mp4: 去除背景音后的视频
      - encoded/merged_XXXp.mp4: 多种分辨率的视频
    
    \b
    示例:
      drama-processor all /path/to/drama
      drama-processor all /path/to/drama --specs 1080p --specs 720p
      drama-processor all /path/to/drama --model spleeter:2stems --specs 480p
      drama-processor all /path/to/drama --accompaniment-volume 0.2
    """
    try:
        # 验证伴奏音量参数
        if not 0.0 <= accompaniment_volume <= 1.0:
            raise click.BadParameter("伴奏音量必须在 0.0 到 1.0 之间")
        
        # 解析转码规格
        transcode_specs = parse_transcode_specs(specs)
        
        # 如果提供了配置文件，从文件加载配置
        if config:
            processing_config = ConfigManager.load_from_file(Path(config))
            # 命令行参数覆盖配置文件
            processing_config.drama_root = drama_root
            processing_config.max_workers = workers
            processing_config.enable_resume = False
            processing_config.audio_separator_model = model
            processing_config.transcode_specs = transcode_specs
            processing_config.log_level = log_level
        else:
            # 从命令行选项创建配置
            processing_config = create_config_from_options(
                drama_root, workers, False, log_level,
                log_file, None, report_dir,
                transcode_specs
            )
            processing_config.audio_separator_model = model
        
        # 添加伴奏音量配置
        processing_config.accompaniment_volume = accompaniment_volume
        
        specs_str = ', '.join([spec.resolution_name for spec in transcode_specs])
        click.echo(f"开始完整处理流程: {drama_root}")
        click.echo(f"配置: 并发数={workers}, 模型={model}, 伴奏音量={accompaniment_volume*100:.0f}%, 规格=[{specs_str}]")
        click.echo("")
        
        # 导入处理函数
        from .main import run_merge, run_separate, run_transcode
        
        # 步骤 1: 合并视频
        click.echo("=" * 60)
        click.echo("步骤 1/3: 合并视频和字幕")
        click.echo("=" * 60)
        success = run_merge(processing_config)
        if not success:
            click.echo("合并步骤失败，终止处理", err=True)
            sys.exit(1)
        click.echo("")
        
        # 步骤 2: 分离音频
        click.echo("=" * 60)
        click.echo("步骤 2/3: 分离音频（去除背景音）")
        click.echo("=" * 60)
        success = run_separate(processing_config)
        if not success:
            click.echo("音频分离步骤失败，终止处理", err=True)
            sys.exit(1)
        click.echo("")
        
        # 步骤 3: 转码视频
        click.echo("=" * 60)
        click.echo("步骤 3/3: 转码视频为多种规格")
        click.echo("=" * 60)
        success = run_transcode(processing_config)
        if not success:
            click.echo("转码步骤失败", err=True)
            sys.exit(1)
        click.echo("")
        
        # 完成
        click.echo("=" * 60)
        click.echo("✓ 完整处理流程已完成")
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


def main():
    """主入口函数"""
    cli()


if __name__ == '__main__':
    main()
