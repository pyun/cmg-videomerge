# GPU 加速支持

本工具现已支持 GPU 加速，可显著提升视频转码和音频分离的处理速度。

## 功能概述

### 1. 视频转码 GPU 加速（FFmpeg）

支持以下 GPU 编码器：
- **NVIDIA NVENC** (`h264_nvenc`) - NVIDIA GPU 硬件编码
- **Intel Quick Sync Video** (`h264_qsv`) - Intel 集成显卡硬件编码
- **VideoToolbox** (`h264_videotoolbox`) - macOS 硬件加速

### 2. 音频分离 GPU 加速（TensorFlow/Spleeter）

- 使用 TensorFlow GPU 版本加速 Spleeter 音频分离
- 需要 NVIDIA GPU + CUDA + cuDNN

## 当前系统状态

根据检测结果：

### FFmpeg 转码
- ✓ **检测到 Intel GPU**
- ✓ **可用编码器**: `h264_qsv` (Intel Quick Sync Video)
- ✗ 未检测到 NVIDIA GPU
- 💡 **建议**: 使用 `--gpu` 选项启用 Intel Quick Sync 加速

### Spleeter 音频分离
- ✗ **TensorFlow 未检测到 GPU**
- 原因: 未安装 NVIDIA GPU 驱动或 CUDA
- 当前使用 CPU 进行音频分离
- 💡 **建议**: 如果有 NVIDIA GPU，安装驱动和 CUDA 以获得更快的处理速度

## 使用方法

### 启用 GPU 加速转码

```bash
# 使用 GPU 加速（自动检测可用的 GPU 编码器）
drama-processor transcode /path/to/drama --gpu

# 指定编码预设（影响速度和质量）
drama-processor transcode /path/to/drama --gpu --preset fast

# 完整示例
drama-processor transcode /path/to/drama \
  --gpu \
  --preset medium \
  --specs 1080p --specs 720p \
  --workers 4
```

### 编码预设选项

- `ultrafast` - 最快速度，质量较低
- `fast` - 快速编码，质量中等
- `medium` - 平衡速度和质量（默认）
- `slow` - 较慢速度，质量较高
- `veryslow` - 最慢速度，质量最高

### 查看 GPU 状态

运行任何转码或分离命令时，程序会自动显示 GPU 检测结果：

```bash
# 转码时会显示 GPU 状态
drama-processor transcode /path/to/drama --gpu

# 音频分离时会显示 TensorFlow GPU 状态
drama-processor separate /path/to/drama
```

## 性能对比

### Intel Quick Sync Video (当前可用)

| 操作 | CPU 编码 | QSV 加速 | 提升 |
|------|---------|---------|------|
| 1080p 转码 | ~2-3x 实时 | ~5-8x 实时 | 2-3倍 |
| 720p 转码 | ~3-4x 实时 | ~8-12x 实时 | 2-3倍 |

### NVIDIA NVENC（如果安装）

| 操作 | CPU 编码 | NVENC 加速 | 提升 |
|------|---------|-----------|------|
| 1080p 转码 | ~2-3x 实时 | ~10-15x 实时 | 4-5倍 |
| 720p 转码 | ~3-4x 实时 | ~15-20x 实时 | 4-5倍 |

### TensorFlow GPU（音频分离）

| 操作 | CPU | GPU (CUDA) | 提升 |
|------|-----|-----------|------|
| Spleeter 2stems | ~0.3x 实时 | ~2-3x 实时 | 6-10倍 |

## 安装 NVIDIA GPU 支持（可选）

如果您的系统有 NVIDIA GPU，可以安装以下组件以获得更好的性能：

### 1. 安装 NVIDIA 驱动

```bash
# 检查可用的驱动版本
ubuntu-drivers devices

# 安装推荐的驱动
sudo ubuntu-drivers autoinstall

# 或手动安装特定版本
sudo apt install nvidia-driver-535

# 重启系统
sudo reboot

# 验证安装
nvidia-smi
```

### 2. 安装 CUDA（用于 TensorFlow GPU）

```bash
# 安装 CUDA 11.2（TensorFlow 2.5 兼容版本）
wget https://developer.download.nvidia.com/compute/cuda/11.2.0/local_installers/cuda_11.2.0_460.27.04_linux.run
sudo sh cuda_11.2.0_460.27.04_linux.run

# 添加到环境变量
echo 'export PATH=/usr/local/cuda-11.2/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.2/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### 3. 安装 cuDNN

```bash
# 下载 cuDNN 8.1（需要 NVIDIA 账号）
# https://developer.nvidia.com/cudnn

# 解压并安装
tar -xzvf cudnn-11.2-linux-x64-v8.1.0.77.tgz
sudo cp cuda/include/cudnn*.h /usr/local/cuda/include
sudo cp cuda/lib64/libcudnn* /usr/local/cuda/lib64
sudo chmod a+r /usr/local/cuda/include/cudnn*.h /usr/local/cuda/lib64/libcudnn*
```

### 4. 安装 TensorFlow GPU（可选）

```bash
# 如果需要 GPU 加速音频分离
pip install tensorflow-gpu==2.5.0
```

## 故障排除

### FFmpeg GPU 编码失败

如果启用 `--gpu` 后转码失败：

```bash
# 检查 FFmpeg 支持的编码器
ffmpeg -encoders | grep h264

# 如果失败，程序会自动回退到 CPU 编码
# 查看日志了解详细错误信息
drama-processor transcode /path/to/drama --gpu --log-level DEBUG
```

### TensorFlow 找不到 GPU

```bash
# 检查 CUDA 安装
nvcc --version

# 检查 TensorFlow 是否能看到 GPU
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"

# 如果返回空列表，检查 CUDA 和 cuDNN 版本是否匹配
```

## 测试 GPU 检测

运行测试脚本查看详细的 GPU 检测信息：

```bash
python test_gpu_detection.py
```

输出示例：
```
============================================================
GPU 加速状态检测
============================================================
✗ 未检测到 NVIDIA GPU
✓ 检测到 Intel GPU

✓ GPU 加速: 已启用
  使用编码器: h264_qsv
  类型: Intel Quick Sync Video
============================================================
```

## 建议

1. **视频转码**: 
   - ✅ 使用 `--gpu` 启用 Intel Quick Sync 加速
   - 使用 `--preset fast` 或 `medium` 获得最佳速度/质量平衡

2. **音频分离**:
   - 当前使用 CPU，性能已足够
   - 如需更快速度，考虑安装 NVIDIA GPU + CUDA

3. **批量处理**:
   - 使用 `--workers` 参数并发处理多个视频
   - GPU 加速 + 多线程可获得最佳性能

## 示例命令

```bash
# 完整流程，启用所有优化
drama-processor all /path/to/drama \
  --gpu \
  --preset fast \
  --workers 4 \
  --specs 1080p --specs 720p

# 仅转码，使用 GPU 加速
drama-processor transcode /path/to/drama \
  --gpu \
  --preset medium \
  --specs 1080p --specs 720p --specs 480p

# 音频分离（自动检测 TensorFlow GPU）
drama-processor separate /path/to/drama \
  --workers 2
```
