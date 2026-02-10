#!/usr/bin/env python3
"""
GPU 检测测试脚本

测试 FFmpeg GPU 编码器和 TensorFlow GPU 支持的检测功能。
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_ffmpeg_gpu():
    """测试 FFmpeg GPU 检测"""
    print("=" * 70)
    print("测试 FFmpeg GPU 加速检测")
    print("=" * 70)
    
    from drama_processor.ffmpeg_wrapper import OptimizedFFmpegWrapper
    
    # 测试禁用 GPU
    print("\n1. 测试禁用 GPU 模式:")
    wrapper_no_gpu = OptimizedFFmpegWrapper(enable_gpu=False)
    
    # 测试启用 GPU
    print("\n2. 测试启用 GPU 模式:")
    wrapper_with_gpu = OptimizedFFmpegWrapper(enable_gpu=True)
    
    print("\n" + "=" * 70)


def test_tensorflow_gpu():
    """测试 TensorFlow GPU 检测"""
    print("\n" + "=" * 70)
    print("测试 TensorFlow (Spleeter) GPU 加速检测")
    print("=" * 70)
    
    from drama_processor.separator import AudioSeparator
    
    # 创建音频分离器会自动检测 GPU
    separator = AudioSeparator()
    
    print("\n" + "=" * 70)


def main():
    """主函数"""
    print("\n")
    print("*" * 70)
    print("GPU 加速检测测试")
    print("*" * 70)
    
    try:
        # 测试 FFmpeg GPU
        test_ffmpeg_gpu()
        
        # 测试 TensorFlow GPU
        test_tensorflow_gpu()
        
        print("\n" + "*" * 70)
        print("测试完成！")
        print("*" * 70 + "\n")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
