"""
文件管理模块

提供文件和目录管理功能。
"""

import shutil
from pathlib import Path
from typing import Optional


class FileManager:
    """文件管理器
    
    提供文件复制、目录创建、命名冲突处理等功能。
    """
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """确保目录存在
        
        如果目录不存在则创建。
        
        Args:
            path: 目录路径
        """
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def copy_file(src: Path, dst: Path) -> Path:
        """复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            实际的目标文件路径
        """
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst
    
    @staticmethod
    def get_unique_path(path: Path) -> Path:
        """获取唯一的文件路径
        
        如果文件已存在，添加数字后缀。
        
        Args:
            path: 原始文件路径
            
        Returns:
            唯一的文件路径
        """
        if not path.exists():
            return path
        
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    @staticmethod
    def get_file_size(path: Path) -> int:
        """获取文件大小
        
        Args:
            path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        return path.stat().st_size if path.exists() else 0
    
    @staticmethod
    def get_directory_size(path: Path) -> int:
        """获取目录大小
        
        Args:
            path: 目录路径
            
        Returns:
            目录总大小（字节）
        """
        total = 0
        if path.exists() and path.is_dir():
            for f in path.rglob('*'):
                if f.is_file():
                    total += f.stat().st_size
        return total
    
    @staticmethod
    def clean_directory(path: Path) -> None:
        """清空目录
        
        删除目录下的所有文件和子目录。如果目录不存在，则创建它。
        
        Args:
            path: 目录路径
        """
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
