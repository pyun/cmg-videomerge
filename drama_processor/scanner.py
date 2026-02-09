"""
目录扫描器

扫描和验证短剧目录结构。

本模块实现了 DirectoryScanner 类，用于：
- 扫描 drama/ 根目录，识别符合 drama-XXXX 命名模式的子目录
- 验证目录结构是否满足各功能模块的要求

验证需求：5.1, 5.2, 5.3, 5.4
"""

import re
from pathlib import Path
from typing import List, Optional

from .models import DramaDirectory


# drama-XXXX 命名模式的正则表达式
# 支持格式：drama-0001, drama-1234, drama-9999 等
DRAMA_DIR_PATTERN = re.compile(r'^drama-\d{4}$')


class DirectoryScanner:
    """目录扫描器
    
    扫描 drama/ 根目录，识别符合命名规范的短剧目录，
    并验证目录结构是否满足各功能模块的要求。
    
    目录结构示例：
        drama/
        ├── drama-0001/
        │   ├── video/          # 原始视频片段
        │   ├── srt/            # 字幕文件
        │   ├── merged/         # 合并后的视频和字幕
        │   └── cleared/        # 去除背景音后的视频
        ├── drama-0002/
        │   └── ...
        └── ...
    
    Attributes:
        pattern: 目录命名模式的正则表达式
    """
    
    def __init__(self, pattern: Optional[re.Pattern] = None):
        """初始化目录扫描器
        
        Args:
            pattern: 自定义的目录命名模式正则表达式，
                    默认为 drama-XXXX 格式
        """
        self.pattern = pattern or DRAMA_DIR_PATTERN
    
    def _is_valid_drama_dir_name(self, name: str) -> bool:
        """检查目录名是否符合 drama-XXXX 命名模式
        
        Args:
            name: 目录名称
            
        Returns:
            是否符合命名模式
        """
        return bool(self.pattern.match(name))
    
    def _check_subdirectory(self, drama_path: Path, subdir_name: str) -> bool:
        """检查子目录是否存在
        
        支持两种目录结构：
        1. drama_path/subdir_name（旧格式）
        2. drama_path/original/subdir_name（新格式）
        
        Args:
            drama_path: 短剧目录路径
            subdir_name: 子目录名称
            
        Returns:
            子目录是否存在
        """
        # 首先检查 original/ 子目录（新格式）
        original_subdir = drama_path / "original" / subdir_name
        if original_subdir.exists() and original_subdir.is_dir():
            return True
        
        # 回退到直接子目录（旧格式）
        direct_subdir = drama_path / subdir_name
        return direct_subdir.exists() and direct_subdir.is_dir()
    
    def _create_drama_directory(self, path: Path) -> DramaDirectory:
        """创建 DramaDirectory 对象
        
        检查目录结构并创建对应的数据对象。
        
        Args:
            path: 短剧目录路径
            
        Returns:
            DramaDirectory 对象，包含目录结构信息
        """
        return DramaDirectory(
            path=path,
            name=path.name,
            has_video_dir=self._check_subdirectory(path, 'video'),
            has_srt_dir=self._check_subdirectory(path, 'srt'),
            has_merged_dir=self._check_subdirectory(path, 'merged'),
            has_cleared_dir=self._check_subdirectory(path, 'cleared')
        )
    
    def scan_drama_root(self, root_path: Path) -> List[DramaDirectory]:
        """扫描 drama/ 根目录
        
        识别所有符合 drama-XXXX 命名模式的子目录，并检查其目录结构。
        
        验证需求 5.1：识别所有符合 drama-XXXX 命名模式的子目录
        
        Args:
            root_path: drama/ 根目录路径
            
        Returns:
            短剧目录列表，按目录名排序
            
        Raises:
            FileNotFoundError: 如果根目录不存在
            NotADirectoryError: 如果路径不是目录
        """
        # 验证根目录
        if not root_path.exists():
            raise FileNotFoundError(f"根目录不存在: {root_path}")
        
        if not root_path.is_dir():
            raise NotADirectoryError(f"路径不是目录: {root_path}")
        
        drama_dirs: List[DramaDirectory] = []
        
        # 遍历根目录下的所有子目录
        for item in root_path.iterdir():
            # 只处理目录
            if not item.is_dir():
                continue
            
            # 检查目录名是否符合 drama-XXXX 模式
            if self._is_valid_drama_dir_name(item.name):
                drama_dir = self._create_drama_directory(item)
                drama_dirs.append(drama_dir)
        
        # 按目录名排序（自然排序，drama-0001 在 drama-0002 之前）
        drama_dirs.sort(key=lambda d: d.name)
        
        return drama_dirs
    
    def validate_for_merge(self, drama_dir: DramaDirectory) -> bool:
        """验证目录是否适合合并操作
        
        合并操作需要 video/ 子目录存在。
        srt/ 子目录是可选的（如果不存在，只合并视频）。
        
        验证需求 5.2：检查 Drama_Directory 下是否存在 video/ 和 srt/ 子目录
        
        Args:
            drama_dir: 短剧目录信息
            
        Returns:
            是否可以执行合并操作（video/ 目录必须存在）
        """
        # video/ 目录是必需的
        return drama_dir.has_video_dir
    
    def validate_for_separation(self, drama_dir: DramaDirectory) -> bool:
        """验证目录是否适合音频分离操作
        
        音频分离操作需要 merged/ 子目录存在。
        
        验证需求 5.3：检查 Drama_Directory 下是否存在 merged/ 子目录
        
        Args:
            drama_dir: 短剧目录信息
            
        Returns:
            是否可以执行音频分离操作
        """
        return drama_dir.has_merged_dir
    
    def validate_for_transcode(self, drama_dir: DramaDirectory) -> bool:
        """验证目录是否适合转码操作
        
        转码操作需要 cleared/ 子目录存在。
        
        验证需求 5.4：检查 Drama_Directory 下是否存在 cleared/ 子目录
        
        Args:
            drama_dir: 短剧目录信息
            
        Returns:
            是否可以执行转码操作
        """
        return drama_dir.has_cleared_dir
    
    def get_valid_dirs_for_merge(
        self, 
        drama_dirs: List[DramaDirectory]
    ) -> List[DramaDirectory]:
        """获取所有适合合并操作的目录
        
        Args:
            drama_dirs: 短剧目录列表
            
        Returns:
            适合合并操作的目录列表
        """
        return [d for d in drama_dirs if self.validate_for_merge(d)]
    
    def get_valid_dirs_for_separation(
        self, 
        drama_dirs: List[DramaDirectory]
    ) -> List[DramaDirectory]:
        """获取所有适合音频分离操作的目录
        
        Args:
            drama_dirs: 短剧目录列表
            
        Returns:
            适合音频分离操作的目录列表
        """
        return [d for d in drama_dirs if self.validate_for_separation(d)]
    
    def get_valid_dirs_for_transcode(
        self, 
        drama_dirs: List[DramaDirectory]
    ) -> List[DramaDirectory]:
        """获取所有适合转码操作的目录
        
        Args:
            drama_dirs: 短剧目录列表
            
        Returns:
            适合转码操作的目录列表
        """
        return [d for d in drama_dirs if self.validate_for_transcode(d)]
    
    def scan_and_validate(
        self, 
        root_path: Path, 
        operation: str
    ) -> List[DramaDirectory]:
        """扫描并验证目录，返回适合指定操作的目录列表
        
        这是一个便捷方法，结合了扫描和验证功能。
        
        Args:
            root_path: drama/ 根目录路径
            operation: 操作类型，可选值：'merge', 'separation', 'transcode'
            
        Returns:
            适合指定操作的目录列表
            
        Raises:
            ValueError: 如果操作类型无效
        """
        # 扫描所有短剧目录
        all_dirs = self.scan_drama_root(root_path)
        
        # 根据操作类型过滤
        if operation == 'merge':
            return self.get_valid_dirs_for_merge(all_dirs)
        elif operation == 'separation':
            return self.get_valid_dirs_for_separation(all_dirs)
        elif operation == 'transcode':
            return self.get_valid_dirs_for_transcode(all_dirs)
        else:
            raise ValueError(
                f"无效的操作类型: {operation}，"
                f"有效值为: 'merge', 'separation', 'transcode'"
            )
