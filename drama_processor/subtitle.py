"""
字幕处理模块

支持 SRT 和 ASS 格式的字幕解析、编辑和保存。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from .models import SubtitleEntry, SubtitleFormat


class SubtitleParser(ABC):
    """字幕解析器基类
    
    定义字幕解析和格式化的接口。
    """
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[SubtitleEntry]:
        """解析字幕文件
        
        Args:
            file_path: 字幕文件路径
            
        Returns:
            字幕条目列表
        """
        pass
    
    @abstractmethod
    def format_entry(self, entry: SubtitleEntry) -> str:
        """格式化单个字幕条目
        
        Args:
            entry: 字幕条目
            
        Returns:
            格式化后的字符串
        """
        pass
    
    @abstractmethod
    def get_header(self) -> str:
        """获取文件头部（ASS 格式需要）
        
        Returns:
            文件头部字符串
        """
        pass


class SRTParser(SubtitleParser):
    """SRT 格式解析器
    
    解析和格式化 SRT (SubRip) 格式的字幕文件。
    
    SRT 格式示例：
        1
        00:00:01,000 --> 00:00:03,000
        第一条字幕
        
        2
        00:00:04,000 --> 00:00:06,000
        第二条字幕
    """
    
    def parse(self, file_path: Path) -> List[SubtitleEntry]:
        """解析 SRT 文件
        
        Args:
            file_path: SRT 文件路径
            
        Returns:
            字幕条目列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        entries = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析 SRT 格式
        # 格式: 序号\n时间戳\n文本\n\n
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # 解析序号
                    index = int(lines[0])
                    
                    # 解析时间戳行: 00:00:01,000 --> 00:00:03,000
                    time_line = lines[1]
                    if ' --> ' not in time_line:
                        continue  # 跳过格式错误的行
                    
                    start_str, end_str = time_line.split(' --> ')
                    start_time = self._parse_srt_time(start_str.strip())
                    end_time = self._parse_srt_time(end_str.strip())
                    
                    # 解析文本（可能多行）
                    text = '\n'.join(lines[2:])
                    
                    entries.append(SubtitleEntry(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        text=text
                    ))
                except (ValueError, IndexError) as e:
                    # 跳过格式错误的块
                    continue
        
        return entries
    
    def _parse_srt_time(self, time_str: str) -> float:
        """解析 SRT 时间格式为秒
        
        Args:
            time_str: SRT 时间字符串，格式为 "HH:MM:SS,mmm"
            
        Returns:
            时间（秒）
            
        Example:
            >>> parser = SRTParser()
            >>> parser._parse_srt_time("00:00:01,500")
            1.5
            >>> parser._parse_srt_time("01:23:45,678")
            5025.678
        """
        # 格式: 00:00:01,000
        # 将逗号替换为点，方便解析毫秒
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _format_srt_time(self, seconds: float) -> str:
        """格式化秒为 SRT 时间格式
        
        Args:
            seconds: 时间（秒）
            
        Returns:
            SRT 时间字符串，格式为 "HH:MM:SS,mmm"
            
        Example:
            >>> parser = SRTParser()
            >>> parser._format_srt_time(1.5)
            '00:00:01,500'
            >>> parser._format_srt_time(5025.678)
            '01:23:45,678'
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millisecs = int((secs % 1) * 1000)
        secs = int(secs)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def format_entry(self, entry: SubtitleEntry) -> str:
        """格式化为 SRT 格式
        
        Args:
            entry: 字幕条目
            
        Returns:
            格式化后的 SRT 字符串
            
        Example:
            >>> parser = SRTParser()
            >>> entry = SubtitleEntry(1, 1.0, 3.0, "Hello")
            >>> parser.format_entry(entry)
            '1\\n00:00:01,000 --> 00:00:03,000\\nHello\\n'
        """
        start = self._format_srt_time(entry.start_time)
        end = self._format_srt_time(entry.end_time)
        return f"{entry.index}\n{start} --> {end}\n{entry.text}\n"
    
    def get_header(self) -> str:
        """SRT 没有头部
        
        Returns:
            空字符串
        """
        return ""


class ASSParser(SubtitleParser):
    """ASS 格式解析器
    
    解析和格式化 ASS (Advanced SubStation Alpha) 格式的字幕文件。
    
    ASS 格式示例：
        [Script Info]
        Title: Example
        
        [V4+ Styles]
        Format: Name, Fontname, Fontsize, ...
        Style: Default,Arial,20,...
        
        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,第一条字幕
    """
    
    def __init__(self):
        """初始化 ASS 解析器
        
        Attributes:
            header_lines: 存储头部信息的行列表
            styles: 存储样式信息的字典
        """
        self.header_lines: List[str] = []
        self.styles: dict = {}
    
    def parse(self, file_path: Path) -> List[SubtitleEntry]:
        """解析 ASS 文件
        
        Args:
            file_path: ASS 文件路径
            
        Returns:
            字幕条目列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        entries = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        in_events = False
        index = 1
        
        for line in lines:
            line = line.strip()
            
            # 检测 [Events] 部分
            if line.startswith('[Events]'):
                in_events = True
                continue
            
            # 保存头部信息（[Events] 之前的所有内容）
            if not in_events:
                self.header_lines.append(line)
                
                # 解析样式信息
                if line.startswith('Style:'):
                    parts = line.split(':', 1)[1].split(',')
                    if parts:
                        style_name = parts[0].strip()
                        self.styles[style_name] = line
                continue
            
            # 解析事件行（Dialogue）
            if line.startswith('Dialogue:'):
                try:
                    # ASS Dialogue 格式：
                    # Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
                    # 注意：Text 部分可能包含逗号，所以只分割前 9 个字段
                    parts = line.split(':', 1)[1].split(',', 9)
                    
                    if len(parts) >= 10:
                        # Layer = parts[0]
                        start_time = self._parse_ass_time(parts[1].strip())
                        end_time = self._parse_ass_time(parts[2].strip())
                        style = parts[3].strip()
                        # Name = parts[4]
                        # MarginL = parts[5]
                        # MarginR = parts[6]
                        # MarginV = parts[7]
                        # Effect = parts[8]
                        text = parts[9].strip()
                        
                        entries.append(SubtitleEntry(
                            index=index,
                            start_time=start_time,
                            end_time=end_time,
                            text=text,
                            style=style
                        ))
                        index += 1
                except (ValueError, IndexError) as e:
                    # 跳过格式错误的行
                    continue
        
        return entries
    
    def _parse_ass_time(self, time_str: str) -> float:
        """解析 ASS 时间格式为秒
        
        Args:
            time_str: ASS 时间字符串，格式为 "H:MM:SS.cc"
            
        Returns:
            时间（秒）
            
        Example:
            >>> parser = ASSParser()
            >>> parser._parse_ass_time("0:00:01.50")
            1.5
            >>> parser._parse_ass_time("1:23:45.67")
            5025.67
        """
        # 格式: 0:00:01.00 或 1:23:45.67
        parts = time_str.split(':')
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _format_ass_time(self, seconds: float) -> str:
        """格式化秒为 ASS 时间格式
        
        Args:
            seconds: 时间（秒）
            
        Returns:
            ASS 时间字符串，格式为 "H:MM:SS.cc"
            
        Example:
            >>> parser = ASSParser()
            >>> parser._format_ass_time(1.5)
            '0:00:01.50'
            >>> parser._format_ass_time(5025.67)
            '1:23:45.67'
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        # ASS 格式使用两位小数的秒数
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    
    def format_entry(self, entry: SubtitleEntry) -> str:
        """格式化为 ASS 格式
        
        Args:
            entry: 字幕条目
            
        Returns:
            格式化后的 ASS Dialogue 行
            
        Example:
            >>> parser = ASSParser()
            >>> entry = SubtitleEntry(1, 1.0, 3.0, "Hello", style="Default")
            >>> parser.format_entry(entry)
            'Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hello\\n'
        """
        start = self._format_ass_time(entry.start_time)
        end = self._format_ass_time(entry.end_time)
        style = entry.style or "Default"
        
        # ASS 格式: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        return f"Dialogue: 0,{start},{end},{style},,0,0,0,,{entry.text}\n"
    
    def get_header(self) -> str:
        """获取 ASS 文件头部
        
        Returns:
            ASS 文件头部字符串，包括 [Script Info]、[V4+ Styles] 和 [Events] 格式行
        """
        # 如果没有头部信息，返回默认头部
        if not self.header_lines:
            return self._get_default_header()
        
        # 返回保存的头部信息，并添加 [Events] 部分的格式行
        header = '\n'.join(self.header_lines)
        header += '\n\n[Events]\n'
        header += 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
        
        return header
    
    def _get_default_header(self) -> str:
        """获取默认的 ASS 文件头部
        
        Returns:
            默认的 ASS 头部字符串
        """
        return """[Script Info]
Title: Default
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


class SubtitleFile:
    """字幕文件
    
    封装字幕文件的解析、编辑和保存操作。
    """
    
    def __init__(
        self, 
        entries: List[SubtitleEntry],
        format: SubtitleFormat,
        parser: SubtitleParser
    ):
        self.entries = entries
        self.format = format
        self.parser = parser
    
    @classmethod
    def parse(cls, file_path: Path) -> 'SubtitleFile':
        """解析字幕文件（自动检测格式）
        
        根据文件扩展名自动检测字幕格式（.srt 或 .ass），
        使用相应的解析器解析文件内容。
        
        Args:
            file_path: 字幕文件路径
            
        Returns:
            SubtitleFile 实例
            
        Raises:
            ValueError: 不支持的字幕格式
            FileNotFoundError: 文件不存在
            
        Example:
            >>> subtitle = SubtitleFile.parse(Path("video.srt"))
            >>> print(f"格式: {subtitle.format}, 条目数: {len(subtitle.entries)}")
            格式: SubtitleFormat.SRT, 条目数: 10
        """
        # 获取文件扩展名（转换为小写）
        ext = file_path.suffix.lower()
        
        # 根据扩展名选择解析器
        if ext == '.srt':
            parser = SRTParser()
            format = SubtitleFormat.SRT
        elif ext == '.ass':
            parser = ASSParser()
            format = SubtitleFormat.ASS
        else:
            raise ValueError(f"不支持的字幕格式: {ext}，仅支持 .srt 和 .ass")
        
        # 解析文件
        entries = parser.parse(file_path)
        
        # 创建并返回 SubtitleFile 实例
        return cls(entries, format, parser)
    
    def save(self, file_path: Path) -> None:
        """保存字幕文件
        
        将字幕条目保存到文件，保持原格式（SRT 或 ASS）。
        自动创建父目录（如果不存在）。
        
        Args:
            file_path: 输出文件路径
            
        Example:
            >>> subtitle = SubtitleFile.parse(Path("input.srt"))
            >>> subtitle.save(Path("output/merged.srt"))
        """
        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 打开文件写入
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入头部（如果有）
            header = self.parser.get_header()
            if header:
                f.write(header)
            
            # 写入所有字幕条目
            for entry in self.entries:
                f.write(self.parser.format_entry(entry))
                
                # SRT 格式需要在每个条目后添加额外的空行
                if self.format == SubtitleFormat.SRT:
                    f.write('\n')
    
    def shift_all(self, offset_seconds: float) -> 'SubtitleFile':
        """偏移所有字幕时间戳
        
        创建一个新的 SubtitleFile 实例，其中所有字幕条目的时间戳
        都偏移了指定的秒数。用于视频合并时调整字幕时间轴。
        
        Args:
            offset_seconds: 偏移量（秒），正数向后偏移，负数向前偏移
            
        Returns:
            新的 SubtitleFile 实例，包含偏移后的字幕条目
            
        Example:
            >>> subtitle = SubtitleFile.parse(Path("video1.srt"))
            >>> # 向后偏移 30 秒（用于合并到第二个视频片段）
            >>> shifted = subtitle.shift_all(30.0)
            >>> shifted.save(Path("video2_shifted.srt"))
        """
        # 对所有条目应用时间戳偏移
        shifted_entries = [
            entry.shift_time(offset_seconds)
            for entry in self.entries
        ]
        
        # 创建并返回新的 SubtitleFile 实例
        # 保持相同的格式和解析器
        return SubtitleFile(shifted_entries, self.format, self.parser)
    
    def get_extension(self) -> str:
        """获取文件扩展名
        
        Returns:
            文件扩展名（如 ".srt" 或 ".ass"）
        """
        return f".{self.format.value}"
