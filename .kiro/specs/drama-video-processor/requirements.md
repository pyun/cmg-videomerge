# 需求文档

## 简介

短剧视频批量处理工具是一个用于自动化处理短剧视频内容的系统。该系统提供三个独立的核心功能：批量合并视频和字幕、批量去除背景音保留人声、批量转码为多个规格。系统设计用于处理存储在标准化目录结构中的多部短剧内容。

## 术语表

- **System**: 短剧视频批量处理工具
- **Drama**: 一部完整的短剧，包含多个视频片段和对应的字幕文件
- **Video_Segment**: 短剧的单个视频片段文件
- **Subtitle_File**: 字幕文件，支持 SRT 和 ASS 格式
- **Merged_Video**: 将多个视频片段合并后的完整视频文件
- **Merged_Subtitle**: 将多个字幕文件合并后的完整字幕文件
- **Vocal_Track**: 视频中的人声音轨
- **Background_Music**: 视频中的背景音乐音轨
- **Transcoded_Video**: 转换为特定分辨率和编码格式的视频文件
- **Drama_Directory**: 存储单部短剧所有文件的目录（格式：drama-XXXX）
- **Merged_Directory**: Drama_Directory 下的 merged/ 子目录，存储合并后的视频和字幕文件
- **Cleared_Directory**: Drama_Directory 下的 cleared/ 子目录，存储去除背景音后的视频和字幕文件
- **Encoded_Directory**: Drama_Directory 下的 encoded/ 子目录，存储转码后的多规格视频文件
- **FFmpeg**: 用于视频和音频处理的开源多媒体框架

## 需求

### 需求 1：批量合并视频和字幕

**用户故事：** 作为内容制作人员，我想要将每部短剧的多个视频片段和字幕文件合并为一个完整的视频文件和对应的字幕文件，以便生成可发布的完整短剧内容。

#### 验收标准

1. WHEN THE System 接收到一个 Drama_Directory 路径，THE System SHALL 读取该目录下 video/ 子目录中的所有视频文件
2. WHEN THE System 读取视频文件时，THE System SHALL 按照文件名的数字顺序（video-001.mp4, video-002.mp4 等）对视频进行排序
3. WHEN THE System 处理字幕文件时，THE System SHALL 从 srt/ 子目录读取所有字幕文件（.srt 或 .ass 格式）并按照文件名顺序排序
4. WHEN THE System 合并视频时，THE System SHALL 使用 FFmpeg 将所有视频片段按顺序连接成一个完整视频
5. WHEN THE System 合并字幕时，THE System SHALL 根据字幕文件格式（SRT 或 ASS）调整每个字幕文件的时间戳以匹配合并后视频的时间轴
6. WHEN 合并操作完成时，THE System SHALL 在 Drama_Directory 的 merged/ 目录下生成名为 merged.mp4 的视频文件
7. WHEN 合并操作完成时，THE System SHALL 在 Drama_Directory 的 merged/ 目录下生成与输入字幕相同格式的合并字幕文件（merged.srt 或 merged.ass）
8. WHEN 处理多个 Drama_Directory 时，THE System SHALL 依次处理每个短剧目录
9. IF 视频文件缺失，THEN THE System SHALL 记录错误信息并跳过该短剧的处理
10. IF 字幕文件缺失，THEN THE System SHALL 仅合并视频文件并记录警告信息

### 需求 2：批量去除背景音保留人声

**用户故事：** 作为内容编辑人员，我想要去除视频中的背景音乐并保留人声对话，以便后期重新配乐或满足特定平台的音频要求。

#### 验收标准

1. WHEN THE System 接收到一个 Drama_Directory 路径，THE System SHALL 从该目录下的 merged/ 子目录读取视频文件
2. WHEN THE System 读取视频文件时，THE System SHALL 使用音频分离技术提取音频轨道
3. WHEN THE System 分离音频时，THE System SHALL 将音频分离为 Vocal_Track 和 Background_Music 两个独立轨道
4. WHEN 音频分离完成时，THE System SHALL 将 Vocal_Track 重新合成到原视频中
5. WHEN 生成输出文件时，THE System SHALL 保持原视频的分辨率和视频编码格式
6. WHEN 处理完成时，THE System SHALL 在 Drama_Directory 下创建 cleared/ 子目录（如果不存在）
7. WHEN 保存输出文件时，THE System SHALL 将去除背景音后的视频文件保存到 cleared/ 目录下
8. WHEN merged/ 目录中存在对应的字幕文件时，THE System SHALL 将字幕文件复制到 cleared/ 目录下
9. WHEN 批量处理多个 Drama_Directory 时，THE System SHALL 依次处理每个短剧目录
10. IF merged/ 目录不存在或为空，THEN THE System SHALL 记录错误信息并跳过该短剧的处理
11. IF 音频分离失败，THEN THE System SHALL 记录错误信息并继续处理下一个短剧

### 需求 3：批量转码为多个规格

**用户故事：** 作为平台运营人员，我想要将视频转码为多种分辨率和格式，以便适配不同的播放平台和网络环境。

#### 验收标准

1. WHEN THE System 接收到一个 Drama_Directory 路径，THE System SHALL 从该目录下的 cleared/ 子目录读取视频文件
2. WHEN THE System 转码视频时，THE System SHALL 支持以下分辨率：1920x1080 (1080p)、1280x720 (720p)、854x480 (480p)
3. WHEN THE System 转码视频时，THE System SHALL 使用 H.264 视频编码和 AAC 音频编码
4. WHEN 生成输出文件时，THE System SHALL 使用格式 {原文件名}_{分辨率}.mp4 命名视频文件
5. WHEN 处理完成时，THE System SHALL 在 Drama_Directory 下创建 encoded/ 子目录（如果不存在）
6. WHEN 保存输出文件时，THE System SHALL 将所有转码后的视频文件保存到 encoded/ 目录下
7. WHEN cleared/ 目录中存在对应的字幕文件时，THE System SHALL 将字幕文件复制到 encoded/ 目录下
8. WHEN 转码过程中，THE System SHALL 保持视频的宽高比，必要时添加黑边
9. WHEN 批量处理多个 Drama_Directory 时，THE System SHALL 依次处理每个短剧目录
10. IF cleared/ 目录不存在或为空，THEN THE System SHALL 记录错误信息并跳过该短剧的处理
11. IF 输入视频的分辨率低于目标分辨率，THEN THE System SHALL 跳过该目标规格并记录警告信息

### 需求 4：进度显示和错误处理

**用户故事：** 作为系统用户，我想要看到处理进度和错误信息，以便了解任务执行状态和排查问题。

#### 验收标准

1. WHEN THE System 开始处理任务时，THE System SHALL 显示当前正在处理的文件名称
2. WHEN THE System 处理批量任务时，THE System SHALL 显示已完成和总任务数量的进度信息
3. WHEN THE System 处理单个文件时，THE System SHALL 显示该文件的处理进度百分比
4. IF 处理过程中发生错误，THEN THE System SHALL 记录详细的错误信息包括文件路径和错误原因
5. WHEN 批量任务完成时，THE System SHALL 显示成功处理和失败处理的文件统计信息
6. WHEN 发生错误时，THE System SHALL 继续处理剩余文件而不是终止整个批量任务

### 需求 5：目录结构和文件管理

**用户故事：** 作为系统管理员，我想要系统能够正确识别和处理标准化的目录结构，以便确保批量处理的可靠性。

#### 验收标准

1. WHEN THE System 扫描 drama/ 根目录时，THE System SHALL 识别所有符合 drama-XXXX 命名模式的子目录
2. WHEN THE System 执行合并功能时，THE System SHALL 检查 Drama_Directory 下是否存在 video/ 和 srt/ 子目录
3. WHEN THE System 执行音频分离功能时，THE System SHALL 检查 Drama_Directory 下是否存在 merged/ 子目录
4. WHEN THE System 执行转码功能时，THE System SHALL 检查 Drama_Directory 下是否存在 cleared/ 子目录
5. WHEN THE System 读取 video/ 目录时，THE System SHALL 只处理 .mp4 格式的视频文件
6. WHEN THE System 读取 srt/ 目录时，THE System SHALL 处理 .srt 和 .ass 格式的字幕文件
7. WHEN THE System 创建输出目录时，THE System SHALL 自动创建不存在的目录（merged/、cleared/、encoded/）
8. IF Drama_Directory 缺少功能所需的输入目录，THEN THE System SHALL 记录错误信息并跳过该目录
9. WHEN THE System 创建输出文件时，THE System SHALL 确保不覆盖已存在的同名文件，而是添加数字后缀

### 需求 6：独立功能模块

**用户故事：** 作为开发人员，我想要每个功能可以独立运行，以便根据实际需求灵活使用不同的处理功能。

#### 验收标准

1. THE System SHALL 提供独立的命令或接口来执行视频合并功能
2. THE System SHALL 提供独立的命令或接口来执行音频分离功能
3. THE System SHALL 提供独立的命令或接口来执行视频转码功能
4. WHEN 执行单个功能时，THE System SHALL 不依赖其他功能模块的执行结果
5. WHEN 用户指定功能参数时，THE System SHALL 只执行指定的功能而不执行其他功能
