"""
状态管理模块

提供断点续传功能的状态持久化。
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import ProcessingStatus


@dataclass
class ProcessingState:
    """处理状态记录
    
    Attributes:
        drama_dir: 短剧目录路径
        operation: 操作类型 ("merge", "separate", "transcode")
        status: 处理状态
        timestamp: 时间戳
        output_files: 输出文件列表
        error_message: 错误信息（如果失败）
    """
    drama_dir: str
    operation: str
    status: ProcessingStatus
    timestamp: str
    output_files: List[str]
    error_message: Optional[str] = None


class StateManager:
    """状态管理器
    
    管理处理状态的持久化，支持断点续传。
    """
    
    def __init__(self, state_file: Path):
        """初始化状态管理器
        
        Args:
            state_file: 状态文件路径
        """
        self.state_file = state_file
        self.states: Dict[str, ProcessingState] = {}
        self.load_state()
    
    def load_state(self) -> None:
        """加载状态文件"""
        if not self.state_file.exists():
            self.states = {}
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换为 ProcessingState 对象
            self.states = {}
            for key, state_dict in data.items():
                self.states[key] = ProcessingState(
                    drama_dir=state_dict['drama_dir'],
                    operation=state_dict['operation'],
                    status=ProcessingStatus(state_dict['status']),
                    timestamp=state_dict['timestamp'],
                    output_files=state_dict['output_files'],
                    error_message=state_dict.get('error_message')
                )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 状态文件损坏,重新开始
            self.states = {}
    
    def save_state(self) -> None:
        """保存状态文件"""
        # 确保父目录存在
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为可序列化的字典
        data = {}
        for key, state in self.states.items():
            data[key] = {
                'drama_dir': state.drama_dir,
                'operation': state.operation,
                'status': state.status.value,
                'timestamp': state.timestamp,
                'output_files': state.output_files,
                'error_message': state.error_message
            }
        
        # 写入文件
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_state_key(self, drama_dir: Path, operation: str) -> str:
        """生成状态键
        
        Args:
            drama_dir: 短剧目录路径
            operation: 操作类型
            
        Returns:
            状态键字符串
        """
        return f"{drama_dir.name}:{operation}"
    
    def is_completed(self, drama_dir: Path, operation: str) -> bool:
        """检查任务是否已完成
        
        Args:
            drama_dir: 短剧目录路径
            operation: 操作类型
            
        Returns:
            是否已完成
        """
        key = self.get_state_key(drama_dir, operation)
        
        if key not in self.states:
            return False
        
        state = self.states[key]
        
        # 检查状态是否为完成
        if state.status != ProcessingStatus.COMPLETED:
            return False
        
        # 验证输出文件是否存在
        for output_file in state.output_files:
            if not Path(output_file).exists():
                return False
        
        return True
    
    def mark_completed(
        self,
        drama_dir: Path,
        operation: str,
        output_files: List[Path]
    ) -> None:
        """标记任务完成
        
        Args:
            drama_dir: 短剧目录路径
            operation: 操作类型
            output_files: 输出文件列表
        """
        key = self.get_state_key(drama_dir, operation)
        
        self.states[key] = ProcessingState(
            drama_dir=str(drama_dir),
            operation=operation,
            status=ProcessingStatus.COMPLETED,
            timestamp=datetime.now().isoformat(),
            output_files=[str(f) for f in output_files],
            error_message=None
        )
        
        self.save_state()
    
    def mark_failed(
        self,
        drama_dir: Path,
        operation: str,
        error_message: str
    ) -> None:
        """标记任务失败
        
        Args:
            drama_dir: 短剧目录路径
            operation: 操作类型
            error_message: 错误信息
        """
        key = self.get_state_key(drama_dir, operation)
        
        self.states[key] = ProcessingState(
            drama_dir=str(drama_dir),
            operation=operation,
            status=ProcessingStatus.FAILED,
            timestamp=datetime.now().isoformat(),
            output_files=[],
            error_message=error_message
        )
        
        self.save_state()
    
    def get_pending_tasks(
        self,
        drama_dirs: List[Path],
        operation: str
    ) -> List[Path]:
        """获取待处理的任务列表
        
        Args:
            drama_dirs: 短剧目录列表
            operation: 操作类型
            
        Returns:
            待处理的目录列表
        """
        pending = []
        
        for drama_dir in drama_dirs:
            if not self.is_completed(drama_dir, operation):
                pending.append(drama_dir)
        
        return pending
    
    def get_summary(self) -> Dict[str, int]:
        """获取处理摘要
        
        Returns:
            包含统计信息的字典
        """
        summary = {
            'total': len(self.states),
            'completed': 0,
            'failed': 0,
            'pending': 0
        }
        
        for state in self.states.values():
            if state.status == ProcessingStatus.COMPLETED:
                summary['completed'] += 1
            elif state.status == ProcessingStatus.FAILED:
                summary['failed'] += 1
            else:
                summary['pending'] += 1
        
        return summary
