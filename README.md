# 短剧视频批量处理工具

一款专为短剧内容制作流程设计的批量视频处理工具，提供视频合并、音频分离、视频转码三大核心功能。

## 功能特性

- **视频合并** - 将多个视频片段和字幕文件合并为单个完整视频
- **音频分离** - 使用 AI 技术去除背景音乐，保留人声对话
- **视频转码** - 将视频转换为多种分辨率和格式
- **并发处理** - 支持多线程并发处理，提高效率
- **字幕支持** - 支持 SRT 和 ASS 字幕格式
- **详细日志** - 生成详细的处理报告和日志

## 系统要求

- Python 3.9+
- FFmpeg 4.0+
- 足够的磁盘空间和内存（音频分离需要较大内存）

## 安装

### 1. 安装 FFmpeg

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg
```

### 2. 安装工具

```bash
# 克隆或下载项目
cd drama-video-processor

# 安装为命令行工具（推荐）
pip install -e .

# 或仅安装依赖
pip install -r requirements.txt
```

### 3. 验证安装

```bash
# 验证 FFmpeg
ffmpeg -version

# 验证工具
drama-processor --version
```

## 目录结构

工具支持两种目录格式：

### 格式 1：直接子目录（旧版）

```
drama/drama-0001/
├── video/                   # 视频片段
│   ├── video-001.mp4
│   ├── video-002.mp4
│   └── ...
├── srt/                     # 字幕文件
│   ├── srt-001.srt
│   ├── srt-002.srt
│   └── ...
├── merged/                  # 合并输出（自动创建）
├── cleared/                 # 音频分离输出（自动创建）
└── encoded/                 # 转码输出（自动创建）
```

### 格式 2：original 子目录（推荐）

```
drama/drama-0001/
├── original/
│   ├── video/              # 视频片段
│   │   ├── video-001.mp4
│   │   └── ...
│   └── srt/                # 字幕文件
│       ├── srt-001.srt
│       └── ...
├── merged/                 # 合并输出（自动创建）
├── cleared/                # 音频分离输出（自动创建）
└── encoded/                # 转码输出（自动创建）
```

## 使用方法

### 1. 视频合并

将 video/ 目录下的视频片段和 srt/ 目录下的字幕文件合并为单个视频。

```bash
# 基本用法
drama-processor merge /path/to/drama

# 使用 8 个并发线程
drama-processor merge /path/to/drama --workers 8

# 启用调试日志
drama-processor merge /path/to/drama --log-level DEBUG
```

**输出：**
- `merged/merged.mp4` - 合并后的视频
- `merged/merged.srt` 或 `merged.ass` - 合并后的字幕

### 2. 音频分离（去除背景音）

从 merged/ 目录读取视频，分离人声和背景音乐，输出只保留人声的视频。

```bash
# 完全去除背景音（默认）
drama-processor separate /path/to/drama

# 保留 20% 伴奏音量（推荐，可保留碰撞、摔打等音效）
drama-processor separate /path/to/drama --accompaniment-volume 0.2

# 保留 50% 伴奏音量
drama-processor separate /path/to/drama -a 0.5

# 使用 4stems 模型（更精细的分离）
drama-processor separate /path/to/drama --model spleeter:4stems
```

**伴奏音量控制：**
- `0.0` - 完全去除伴奏（默认）
- `0.2` - 保留 20% 伴奏音量（推荐，可保留部分音效）
- `0.5` - 保留 50% 伴奏音量
- `1.0` - 保留 100% 伴奏音量（相当于不处理）

**输出：**
- `cleared/merged.mp4` - 去除背景音后的视频
- `cleared/merged.srt` 或 `merged.ass` - 复制的字幕文件

**注意事项：**
- 音频分离需要较大内存，长视频会自动分段处理
- 首次运行会自动下载 Spleeter 模型（约 300MB）
- 模型存储在 `~/.cache/spleeter/`

### 3. 视频转码

从 cleared/ 目录读取视频，转码为多种分辨率。

```bash
# 使用默认规格（1080p, 720p, 480p）
drama-processor transcode /path/to/drama

# 指定转码规格
drama-processor transcode /path/to/drama --specs 1080p --specs 720p

# 使用自定义分辨率
drama-processor transcode /path/to/drama --specs 1920x1080 --specs 1280x720

# 指定单个规格
drama-processor transcode /path/to/drama --specs 480p
```

**支持的规格：**
- 预定义：`1080p`, `720p`, `480p`, `360p`, `240p`
- 自定义：`宽度x高度`（如 `1920x1080`）

**输出：**
- `encoded/merged_1080p.mp4` - 1080p 视频
- `encoded/merged_720p.mp4` - 720p 视频
- `encoded/merged_480p.mp4` - 480p 视频
- `encoded/merged.srt` 或 `merged.ass` - 复制的字幕文件

### 4. 完整流程（一键处理）

依次执行合并、分离、转码三个步骤。

```bash
# 基本用法
drama-processor all /path/to/drama

# 完整配置
drama-processor all /path/to/drama \
  --workers 4 \
  --model spleeter:2stems \
  --accompaniment-volume 0.2 \
  --specs 1080p \
  --specs 720p

# 简化写法
drama-processor all /path/to/drama -w 4 -a 0.2 -s 1080p -s 720p
```

## 常用选项

### 全局选项

```bash
--workers, -w          # 并发处理数量（默认：4）
--log-level, -l        # 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
--log-file             # 日志文件路径
--report-dir           # 报告输出目录（默认：reports/）
--config, -c           # 配置文件路径（JSON 格式）
```

### 音频分离选项

```bash
--model, -m                    # 音频分离模型（默认：spleeter:2stems）
--accompaniment-volume, -a     # 伴奏保留音量（0.0-1.0，默认：0.0）
```

### 转码选项

```bash
--specs, -s            # 转码规格（可多次指定）
```

## 使用示例

### 示例 1：处理单个短剧

```bash
# 完整流程，保留 20% 伴奏音量，输出 1080p 和 720p
drama-processor all /data/drama/drama-0001 \
  --accompaniment-volume 0.2 \
  --specs 1080p \
  --specs 720p
```

### 示例 2：批量处理多个短剧

```bash
# 处理 drama 目录下的所有短剧
drama-processor all /data/drama \
  --workers 8 \
  --accompaniment-volume 0.2
```

### 示例 3：仅去除背景音

```bash
# 先合并
drama-processor merge /data/drama/drama-0001

# 再分离音频，保留部分音效
drama-processor separate /data/drama/drama-0001 --accompaniment-volume 0.2
```

### 示例 4：调试模式

```bash
# 启用详细日志并保存到文件
drama-processor all /data/drama/drama-0001 \
  --log-level DEBUG \
  --log-file debug.log
```

## 处理报告

每次处理完成后，工具会在 `reports/` 目录生成详细的 JSON 报告：

```
reports/
├── merge_report_20260209_120000.json
├── separate_report_20260209_120500.json
└── transcode_report_20260209_121000.json
```

报告包含：
- 处理时间
- 成功/失败任务列表
- 错误信息
- 处理统计

## 故障排除

### 1. 内存不足

**问题：** Spleeter 处理长视频时被系统终止（OOM）

**解决：**
- 工具会自动将长视频（>10分钟）分段处理
- 如仍然内存不足，可增加系统 swap 空间
- 或减少并发数量：`--workers 1`

### 2. FFmpeg 未找到

**问题：** `command not found: ffmpeg`

**解决：**
```bash
# 安装 FFmpeg
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg      # CentOS/RHEL
brew install ffmpeg          # macOS
```

### 3. Spleeter 模型下载失败

**问题：** 首次运行时模型下载失败

**解决：**
- 检查网络连接
- 手动下载模型到 `~/.cache/spleeter/`
- 或使用代理：`export HTTP_PROXY=http://proxy:port`

### 4. 视频时长不匹配

**问题：** 音频分离后视频变短

**解决：**
- 这通常是 Spleeter duration 参数问题，工具已自动处理
- 如仍有问题，请检查源视频是否完整

### 5. 字幕不同步

**问题：** 合并后字幕时间不对

**解决：**
- 确保字幕文件和视频文件按序号一一对应
- 检查字幕文件格式是否正确（SRT 或 ASS）

## 性能优化

### 并发处理

```bash
# 根据 CPU 核心数调整并发数
# 推荐：CPU 核心数 - 1
drama-processor all /path/to/drama --workers 7
```

### 内存管理

- 音频分离是内存密集型操作
- 长视频会自动分段处理（每段 8 分钟）
- 建议至少 8GB 可用内存

### 磁盘空间

- 合并：约为原视频总大小
- 音频分离：约为原视频大小的 1.5 倍（临时文件）
- 转码：根据规格数量，每个规格约为原视频大小

## 技术栈

- **Python 3.9+** - 主要编程语言
- **FFmpeg** - 视频/音频处理
- **Spleeter 2.3.0** - AI 音频分离
- **Click** - 命令行界面框架
- **psutil** - 系统资源监控

## 音频分离模型

- **spleeter:2stems**（默认）- 人声和伴奏分离
- **spleeter:4stems** - 人声、鼓、贝斯、其他
- **spleeter:5stems** - 人声、鼓、贝斯、钢琴、其他

## 许可证

本项目仅供内部使用。

## 支持

如有问题或建议，请联系开发团队。
