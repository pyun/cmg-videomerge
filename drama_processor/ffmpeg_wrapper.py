"""
FFmpeg 包装器

封装 FFmpeg 命令的执行和输出解析。
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any


@dataclass
class FFmpegCommand:
    """FFmpeg 命令
    
    Attributes:
        inputs: 输入文件路径列表
        output: 输出文件路径
        options: FFmpeg 选项列表
    """
    inputs: List[Path]
    output: Path
    options: List[str]


class FFmpegError(Exception):
    """FFmpeg 执行错误"""
    pass


class FFmpegWrapper:
    """FFmpeg 包装器
    
    封装 FFmpeg 命令的执行，提供视频信息获取等功能。
    """
    
    def execute(
        self, 
        command: FFmpegCommand,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> None:
        """执行 FFmpeg 命令
        
        Args:
            command: FFmpeg 命令对象
            progress_callback: 可选的进度回调函数，参数为进度百分比 (0-100)
            
        Raises:
            FFmpegError: 当 FFmpeg 命令执行失败时
        """
        # 构建完整的命令行
        cmd = self._build_command(command)
        
        # 如果有进度回调，需要获取总时长
        total_duration = None
        if progress_callback and command.inputs:
            try:
                total_duration = self.get_video_duration(command.inputs[0])
            except Exception:
                # 如果无法获取时长，继续执行但不报告进度
                pass
        
        # 执行命令
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # 读取 stderr 输出（FFmpeg 将进度信息输出到 stderr）
            stderr_output = []
            if process.stderr:
                for line in process.stderr:
                    stderr_output.append(line)
                    
                    # 解析进度信息
                    if progress_callback and total_duration:
                        progress = self._parse_progress(line, total_duration)
                        if progress is not None:
                            progress_callback(progress)
            
            # 等待进程完成
            return_code = process.wait()
            
            if return_code != 0:
                error_msg = ''.join(stderr_output)
                raise FFmpegError(
                    f"FFmpeg 命令执行失败 (返回码: {return_code})\n"
                    f"命令: {' '.join(cmd)}\n"
                    f"错误信息: {error_msg}"
                )
                
        except FileNotFoundError:
            raise FFmpegError(
                "未找到 FFmpeg 可执行文件。请确保 FFmpeg 已安装并在 PATH 中。"
            )
        except Exception as e:
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"执行 FFmpeg 命令时发生错误: {str(e)}")
    
    def _build_command(self, command: FFmpegCommand) -> List[str]:
        """构建 FFmpeg 命令行
        
        Args:
            command: FFmpeg 命令对象
            
        Returns:
            完整的命令行参数列表
        """
        cmd = ['ffmpeg']
        
        # 添加输入文件
        for input_path in command.inputs:
            cmd.extend(['-i', str(input_path)])
        
        # 添加选项
        cmd.extend(command.options)
        
        # 添加输出文件
        cmd.append(str(command.output))
        
        return cmd
    
    def _parse_progress(self, line: str, total_duration: float) -> Optional[float]:
        """解析 FFmpeg 输出中的进度信息
        
        Args:
            line: FFmpeg 输出的一行
            total_duration: 视频总时长（秒）
            
        Returns:
            进度百分比 (0-100)，如果无法解析则返回 None
        """
        # FFmpeg 进度输出格式示例：
        # frame=  123 fps= 45 q=28.0 size=    1024kB time=00:00:05.12 bitrate=1638.4kbits/s speed=1.23x
        
        # 提取 time 字段
        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            
            current_time = hours * 3600 + minutes * 60 + seconds
            
            if total_duration > 0:
                progress = (current_time / total_duration) * 100
                # 限制在 0-100 范围内
                return min(100.0, max(0.0, progress))
        
        return None
    
    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """获取视频信息
        
        使用 ffprobe 获取视频的详细信息。
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            包含视频信息的字典，包括：
            - duration: 时长（秒）
            - width: 宽度（像素）
            - height: 高度（像素）
            - codec: 视频编码
            - fps: 帧率
            - bitrate: 比特率
            
        Raises:
            FFmpegError: 当无法获取视频信息时
        """
        if not video_path.exists():
            raise FFmpegError(f"视频文件不存在: {video_path}")
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            
            data = json.loads(result.stdout)
            
            # 提取视频流信息
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise FFmpegError(f"未找到视频流: {video_path}")
            
            # 提取格式信息
            format_info = data.get('format', {})
            
            # 构建返回信息
            info = {
                'duration': float(format_info.get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'codec': video_stream.get('codec_name', ''),
                'bitrate': int(format_info.get('bit_rate', 0)),
            }
            
            # 解析帧率
            fps_str = video_stream.get('r_frame_rate', '0/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                if int(den) != 0:
                    info['fps'] = float(num) / float(den)
                else:
                    info['fps'] = 0.0
            else:
                info['fps'] = float(fps_str)
            
            return info
            
        except FileNotFoundError:
            raise FFmpegError(
                "未找到 ffprobe 可执行文件。请确保 FFmpeg 已安装并在 PATH 中。"
            )
        except subprocess.CalledProcessError as e:
            raise FFmpegError(
                f"ffprobe 执行失败: {e.stderr}"
            )
        except json.JSONDecodeError as e:
            raise FFmpegError(
                f"解析 ffprobe 输出失败: {str(e)}"
            )
        except Exception as e:
            raise FFmpegError(
                f"获取视频信息时发生错误: {str(e)}"
            )
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长（秒）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频时长（秒）
            
        Raises:
            FFmpegError: 当无法获取音频时长时
        """
        if not audio_path.exists():
            raise FFmpegError(f"音频文件不存在: {audio_path}")
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )
            
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            duration = float(format_info.get('duration', 0))
            
            return duration
            
        except FileNotFoundError:
            raise FFmpegError(
                "未找到 ffprobe 可执行文件。请确保 FFmpeg 已安装并在 PATH 中。"
            )
        except subprocess.CalledProcessError as e:
            raise FFmpegError(
                f"ffprobe 执行失败: {e.stderr}"
            )
        except json.JSONDecodeError as e:
            raise FFmpegError(
                f"解析 ffprobe 输出失败: {str(e)}"
            )
        except Exception as e:
            raise FFmpegError(
                f"获取音频时长时发生错误: {str(e)}"
            )
    
    def get_video_duration(self, video_path: Path) -> float:
        """获取视频时长（秒）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频时长（秒）
            
        Raises:
            FFmpegError: 当无法获取视频时长时
        """
        info = self.get_video_info(video_path)
        return info['duration']


@dataclass
class TranscodeSpec:
    """转码规格
    
    Attributes:
        width: 目标宽度（像素）
        height: 目标高度（像素）
        video_codec: 视频编码器，默认 libx264
        audio_codec: 音频编码器，默认 aac
    """
    width: int
    height: int
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    
    @property
    def resolution_name(self) -> str:
        """分辨率名称，如 1080p"""
        return f"{self.height}p"


class OptimizedFFmpegWrapper(FFmpegWrapper):
    """性能优化的 FFmpeg 包装器
    
    提供 GPU 加速编码和优化的视频合并功能。
    
    Attributes:
        enable_gpu: 是否启用 GPU 加速
        preset: 编码预设（ultrafast, fast, medium, slow 等）
        gpu_encoder: 检测到的 GPU 编码器名称
        gpu_info: GPU 信息字典
    """
    
    def __init__(self, enable_gpu: bool = False, preset: str = "medium"):
        """初始化优化的 FFmpeg 包装器
        
        Args:
            enable_gpu: 是否启用 GPU 加速编码
            preset: 编码预设，可选值：
                   - ultrafast: 最快速度，质量较低
                   - superfast, veryfast, faster, fast: 速度递减，质量递增
                   - medium: 平衡速度和质量（默认）
                   - slow, slower, veryslow: 速度递减，质量最高
        """
        super().__init__()
        self.enable_gpu = enable_gpu
        self.preset = preset
        self.gpu_info = self._detect_gpu_hardware()
        self.gpu_encoder = self._detect_gpu_encoder()
        self._print_gpu_status()
    
    def _detect_gpu_hardware(self) -> Dict[str, Any]:
        """检测 GPU 硬件信息
        
        Returns:
            GPU 信息字典，包含：
            - has_nvidia: 是否有 NVIDIA GPU
            - has_intel: 是否有 Intel GPU
            - nvidia_info: NVIDIA GPU 详细信息
            - cuda_available: CUDA 是否可用
        """
        gpu_info = {
            'has_nvidia': False,
            'has_intel': False,
            'nvidia_info': None,
            'cuda_available': False
        }
        
        # 检测 NVIDIA GPU
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                gpu_info['has_nvidia'] = True
                gpu_info['nvidia_info'] = result.stdout.strip()
                
                # 检测 CUDA
                try:
                    cuda_result = subprocess.run(
                        ['nvcc', '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if cuda_result.returncode == 0:
                        gpu_info['cuda_available'] = True
                except:
                    pass
        except:
            pass
        
        # 检测 Intel GPU (通过 /proc/cpuinfo 或 lspci)
        try:
            result = subprocess.run(
                ['lspci'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'Intel' in result.stdout and 'VGA' in result.stdout:
                gpu_info['has_intel'] = True
        except:
            pass
        
        return gpu_info
    
    def _print_gpu_status(self) -> None:
        """打印 GPU 状态信息"""
        print("\n" + "="*60)
        print("GPU 加速状态检测")
        print("="*60)
        
        # 打印硬件检测结果
        if self.gpu_info['has_nvidia']:
            print(f"✓ 检测到 NVIDIA GPU")
            if self.gpu_info['nvidia_info']:
                print(f"  GPU 信息: {self.gpu_info['nvidia_info']}")
            if self.gpu_info['cuda_available']:
                print(f"  CUDA: 可用")
            else:
                print(f"  CUDA: 未安装")
        else:
            print("✗ 未检测到 NVIDIA GPU")
        
        if self.gpu_info['has_intel']:
            print(f"✓ 检测到 Intel GPU")
        else:
            print("✗ 未检测到 Intel GPU")
        
        print()
        
        # 打印编码器状态
        if self.enable_gpu:
            if self.gpu_encoder:
                print(f"✓ GPU 加速: 已启用")
                print(f"  使用编码器: {self.gpu_encoder}")
                
                if 'nvenc' in self.gpu_encoder:
                    print(f"  类型: NVIDIA NVENC 硬件编码")
                elif 'qsv' in self.gpu_encoder:
                    print(f"  类型: Intel Quick Sync Video")
                elif 'videotoolbox' in self.gpu_encoder:
                    print(f"  类型: macOS VideoToolbox")
            else:
                print(f"✗ GPU 加速: 已请求但不可用")
                print(f"  原因: FFmpeg 未检测到支持的 GPU 编码器")
                print(f"  将使用 CPU 编码 (libx264)")
        else:
            print(f"○ GPU 加速: 未启用")
            print(f"  使用 CPU 编码 (libx264)")
        
        print("="*60 + "\n")
    
    def _detect_gpu_encoder(self) -> Optional[str]:
        """检测可用的 GPU 编码器
        
        按优先级检测以下编码器：
        1. h264_nvenc - NVIDIA GPU (NVENC)
        2. h264_qsv - Intel Quick Sync Video
        3. h264_videotoolbox - macOS 硬件加速
        
        Returns:
            可用的 GPU 编码器名称，如果没有可用的 GPU 编码器则返回 None
        """
        if not self.enable_gpu:
            return None
        
        try:
            # 获取 FFmpeg 支持的编码器列表
            result = subprocess.run(
                ['ffmpeg', '-hide_banner', '-encoders'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            encoders_output = result.stdout
            
            # 按优先级检测 GPU 编码器，但要验证硬件是否真的存在
            # NVIDIA NVENC - 需要 NVIDIA GPU
            if 'h264_nvenc' in encoders_output and self.gpu_info['has_nvidia']:
                return 'h264_nvenc'
            
            # Intel Quick Sync - 需要 Intel GPU
            if 'h264_qsv' in encoders_output and self.gpu_info['has_intel']:
                return 'h264_qsv'
            
            # macOS VideoToolbox
            if 'h264_videotoolbox' in encoders_output:
                return 'h264_videotoolbox'
            
        except Exception:
            # 如果检测失败，返回 None（使用 CPU 编码）
            pass
        
        return None
    
    def build_transcode_command(
        self,
        input_path: Path,
        output_path: Path,
        spec: TranscodeSpec
    ) -> List[str]:
        """构建优化的转码命令
        
        根据是否有可用的 GPU 编码器，自动选择最优的编码方式。
        
        Args:
            input_path: 输入视频文件路径
            output_path: 输出视频文件路径
            spec: 转码规格
            
        Returns:
            完整的 FFmpeg 命令行参数列表
        """
        cmd = ['ffmpeg', '-i', str(input_path)]
        
        # 选择视频编码器
        if self.gpu_encoder:
            # 使用 GPU 编码器
            cmd.extend(['-c:v', self.gpu_encoder])
            
            # GPU 编码器特定参数
            if 'nvenc' in self.gpu_encoder:
                # NVIDIA NVENC 预设
                preset_map = {
                    'ultrafast': 'p1',
                    'superfast': 'p2',
                    'veryfast': 'p2',
                    'faster': 'p3',
                    'fast': 'p3',
                    'medium': 'p4',
                    'slow': 'p5',
                    'slower': 'p6',
                    'veryslow': 'p7'
                }
                nvenc_preset = preset_map.get(self.preset, 'p4')
                cmd.extend(['-preset', nvenc_preset])
                # NVENC 质量控制
                cmd.extend(['-cq', '23'])  # 恒定质量模式，23是较好的质量
            elif 'qsv' in self.gpu_encoder:
                # Intel Quick Sync 预设
                cmd.extend(['-preset', self.preset])
                cmd.extend(['-global_quality', '23'])
            elif 'videotoolbox' in self.gpu_encoder:
                # macOS VideoToolbox
                cmd.extend(['-b:v', '0'])  # 使用质量模式
                cmd.extend(['-q:v', '65'])  # 质量参数 (0-100, 100最好)
        else:
            # 使用 CPU 编码器 (libx264)
            cmd.extend(['-c:v', spec.video_codec])
            cmd.extend(['-preset', self.preset])
            # CRF 质量控制：18-28 是合理范围，23 是默认值
            # 数值越小质量越好但文件越大
            cmd.extend(['-crf', '23'])
        
        # 视频缩放（保持宽高比，不添加黑边）
        # force_original_aspect_ratio=decrease: 确保视频不会被拉伸
        # 只缩放，不填充黑边
        scale_filter = (
            f'scale={spec.width}:{spec.height}:'
            f'force_original_aspect_ratio=decrease'
        )
        cmd.extend(['-vf', scale_filter])
        
        # 音频编码器和比特率
        cmd.extend(['-c:a', spec.audio_codec])
        cmd.extend(['-b:a', '128k'])  # 音频比特率 128kbps
        
        # 像素格式（确保兼容性）
        cmd.extend(['-pix_fmt', 'yuv420p'])
        
        # 移动 moov atom 到文件开头（优化流媒体播放）
        cmd.extend(['-movflags', '+faststart'])
        
        # 覆盖输出文件
        cmd.extend(['-y'])
        
        return cmd
    
    def build_merge_command(
        self,
        segments: List[Path],
        output_path: Path
    ) -> List[str]:
        """构建优化的合并命令（使用 concat demuxer）
        
        使用 FFmpeg 的 concat demuxer 进行快速视频合并，不重新编码。
        这是最快的合并方法，因为它直接复制视频流而不进行转码。
        
        注意：所有输入视频必须具有相同的编码参数（分辨率、编码器、帧率等）。
        
        Args:
            segments: 要合并的视频片段路径列表
            output_path: 输出视频文件路径
            
        Returns:
            完整的 FFmpeg 命令行参数列表
        """
        # 创建 concat 列表文件
        concat_file = output_path.parent / 'concat_list.txt'
        
        # 写入文件列表
        with open(concat_file, 'w', encoding='utf-8') as f:
            for segment in segments:
                # 使用绝对路径避免路径问题
                # 使用单引号包裹路径以处理特殊字符
                f.write(f"file '{segment.absolute()}'\n")
        
        # 构建 FFmpeg 命令
        cmd = [
            'ffmpeg',
            '-f', 'concat',      # 使用 concat demuxer
            '-safe', '0',        # 允许使用绝对路径
            '-i', str(concat_file),
            '-c', 'copy',        # 直接复制流，不重新编码（最快）
            '-y',                # 覆盖输出文件
            str(output_path)
        ]
        
        return cmd
