"""
文件排序模块

提供智能文件排序功能，支持自然排序和序列验证。

验证需求：1.2, 1.3
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional, Union


class FileSorter:
    """文件排序器
    
    提供自然排序算法，正确处理文件名中的数字。
    支持多种文件命名格式：
    - video-001.mp4, video-002.mp4
    - video_1.mp4, video_2.mp4
    - 01-intro.mp4, 02-main.mp4
    - episode1.mp4, episode2.mp4
    """
    
    @staticmethod
    def extract_number(filename: str) -> Tuple[int, ...]:
        """从文件名中提取所有数字（不含扩展名部分）
        
        Args:
            filename: 文件名（可以包含或不包含扩展名）
            
        Returns:
            数字元组，如果没有数字则返回 (0,)
            
        Examples:
            >>> FileSorter.extract_number("video-001.mp4")
            (1,)
            >>> FileSorter.extract_number("video-001-part-002.mp4")
            (1, 2)
            >>> FileSorter.extract_number("intro.mp4")
            (0,)
        """
        # 移除扩展名，只处理文件名主体
        stem = Path(filename).stem if '.' in filename else filename
        # 提取所有数字序列
        numbers = re.findall(r'\d+', stem)
        # 转换为整数元组
        return tuple(int(n) for n in numbers) if numbers else (0,)
    
    @staticmethod
    def natural_sort_key(path: Path) -> Tuple[Union[int, str], ...]:
        """自然排序键
        
        将文件名分割为文本和数字部分，数字部分按数值排序，
        文本部分按字典序排序。这样可以实现自然排序：
        video-2.mp4 会排在 video-10.mp4 之前。
        
        支持以下格式：
        - video-001.mp4, video-002.mp4
        - video_1.mp4, video_2.mp4
        - 01-intro.mp4, 02-main.mp4
        - episode1.mp4, episode2.mp4
        
        Args:
            path: 文件路径
            
        Returns:
            排序键元组，包含交替的文本和数字部分
            
        Examples:
            >>> FileSorter.natural_sort_key(Path("video-2.mp4"))
            ('video-', 2)
            >>> FileSorter.natural_sort_key(Path("video-10.mp4"))
            ('video-', 10)
        """
        filename = path.stem  # 不含扩展名的文件名
        
        # 分割文件名为文本和数字部分
        parts: List[Union[int, str]] = []
        for match in re.finditer(r'(\d+)|(\D+)', filename):
            if match.group(1):  # 数字部分
                parts.append(int(match.group(1)))
            else:  # 文本部分
                parts.append(match.group(2).lower())  # 转小写以实现大小写不敏感排序
        
        return tuple(parts) if parts else ('',)
    
    @classmethod
    def sort_files(cls, files: List[Path]) -> List[Path]:
        """排序文件列表
        
        使用自然排序算法，正确处理：
        - video-1.mp4, video-2.mp4, ..., video-10.mp4
        - 而不是: video-1.mp4, video-10.mp4, video-2.mp4
        
        Args:
            files: 文件路径列表
            
        Returns:
            排序后的文件路径列表
            
        Examples:
            >>> files = [Path("video-10.mp4"), Path("video-2.mp4"), Path("video-1.mp4")]
            >>> FileSorter.sort_files(files)
            [Path("video-1.mp4"), Path("video-2.mp4"), Path("video-10.mp4")]
        """
        return sorted(files, key=cls.natural_sort_key)
    
    @classmethod
    def validate_sequence(cls, files: List[Path]) -> Tuple[bool, Optional[str]]:
        """验证文件序列的连续性
        
        检查文件序列是否：
        1. 非空
        2. 没有重复的序号
        3. 序号是连续的（允许从任意数字开始）
        
        Args:
            files: 文件路径列表
            
        Returns:
            (is_valid, error_message) 元组：
            - is_valid: 序列是否有效
            - error_message: 如果无效，返回错误信息；否则为 None
            
        Examples:
            >>> files = [Path("video-1.mp4"), Path("video-2.mp4"), Path("video-3.mp4")]
            >>> FileSorter.validate_sequence(files)
            (True, None)
            
            >>> files = [Path("video-1.mp4"), Path("video-3.mp4")]
            >>> FileSorter.validate_sequence(files)
            (False, "序列不连续，缺失序号: [2]")
        """
        if not files:
            return False, "文件列表为空"
        
        # 提取每个文件的第一个数字（主序号）
        numbers = []
        for f in files:
            extracted = cls.extract_number(f.name)
            # 使用第一个数字作为主序号
            numbers.append(extracted[0])
        
        # 检查是否有重复
        seen = set()
        duplicates = []
        for n in numbers:
            if n in seen:
                if n not in duplicates:
                    duplicates.append(n)
            else:
                seen.add(n)
        
        if duplicates:
            return False, f"发现重复的序号: {sorted(duplicates)}"
        
        # 检查是否连续（允许从任意数字开始）
        sorted_numbers = sorted(numbers)
        start = sorted_numbers[0]
        expected = list(range(start, start + len(sorted_numbers)))
        
        if sorted_numbers != expected:
            missing = set(expected) - set(sorted_numbers)
            if missing:
                return False, f"序列不连续，缺失序号: {sorted(missing)}"
        
        return True, None
