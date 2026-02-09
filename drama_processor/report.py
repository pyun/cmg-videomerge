"""
报告生成模块

生成详细的处理报告。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional


@dataclass
class DetailedProcessingReport:
    """详细处理报告
    
    Attributes:
        operation: 操作类型
        start_time: 开始时间
        end_time: 结束时间
        total_tasks: 总任务数
        successful_tasks: 成功的任务列表
        failed_tasks: 失败的任务列表 (path, error)
        skipped_tasks: 跳过的任务列表 (path, reason)
    """
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tasks: int = 0
    successful_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[Tuple[str, str]] = field(default_factory=list)
    skipped_tasks: List[Tuple[str, str]] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """处理总时长"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tasks == 0:
            return 0.0
        return len(self.successful_tasks) / self.total_tasks * 100
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'operation': self.operation,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'total_tasks': self.total_tasks,
            'successful_count': len(self.successful_tasks),
            'failed_count': len(self.failed_tasks),
            'skipped_count': len(self.skipped_tasks),
            'success_rate': f"{self.success_rate:.2f}%",
            'successful_tasks': self.successful_tasks,
            'failed_tasks': [
                {'path': path, 'error': error}
                for path, error in self.failed_tasks
            ],
            'skipped_tasks': [
                {'path': path, 'reason': reason}
                for path, reason in self.skipped_tasks
            ]
        }
    
    def save_to_file(self, output_path: Path) -> None:
        """保存报告到文件
        
        Args:
            output_path: 输出文件路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def print_summary(self) -> None:
        """打印摘要"""
        print("\n" + "=" * 60)
        print(f"处理报告 - {self.operation}")
        print("=" * 60)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.end_time:
            print(f"结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"总耗时: {self.duration_seconds:.2f} 秒")
        print(f"\n总任务数: {self.total_tasks}")
        print(f"✓ 成功: {len(self.successful_tasks)}")
        print(f"✗ 失败: {len(self.failed_tasks)}")
        print(f"⊘ 跳过: {len(self.skipped_tasks)}")
        print(f"成功率: {self.success_rate:.2f}%")
        
        if self.failed_tasks:
            print("\n失败的任务:")
            for path, error in self.failed_tasks:
                print(f"  ✗ {path}")
                print(f"    原因: {error}")
        
        if self.skipped_tasks:
            print("\n跳过的任务:")
            for path, reason in self.skipped_tasks:
                print(f"  ⊘ {path}")
                print(f"    原因: {reason}")
        
        print("=" * 60 + "\n")
