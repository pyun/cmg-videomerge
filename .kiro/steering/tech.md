# Technology Stack

## Core Technologies

- **Python**: 3.9+
- **FFmpeg**: 4.0+ for video/audio processing
- **Spleeter**: 2.3.0 for AI-powered audio separation
- **Click**: CLI framework for command-line interface
- **psutil**: System resource monitoring

## Build System

Standard Python setuptools-based installation:

```bash
# Install as CLI tool (recommended)
pip install -e .

# Install dependencies only
pip install -r requirements.txt
```

## Common Commands

### Installation & Setup
```bash
# Verify FFmpeg installation
ffmpeg -version

# Spleeter models will be downloaded automatically on first run
# Stored in ~/.cache/spleeter/
```

### Running the Tool
```bash
# Method 1: As installed CLI tool
drama-processor merge /path/to/drama
drama-processor separate /path/to/drama
drama-processor transcode /path/to/drama

# Method 2: As Python module
python -m drama_processor.cli merge /path/to/drama
```

### Common Options
```bash
# Concurrent processing
--workers 8

# Logging
--log-level DEBUG
--log-file debug.log

# Resume control
--resume / --no-resume

# Transcode specifications
--specs 1080p --specs 720p
```

## Key Libraries

- **concurrent.futures.ThreadPoolExecutor**: Parallel processing
- **pathlib**: Path handling
- **dataclasses**: Data structure definitions
- **enum**: Type-safe enumerations
- **abc**: Abstract base classes for interfaces

## External Dependencies

- **FFmpeg**: Must be installed separately and available in PATH
- **Spleeter models**: Downloaded automatically on first run (~300MB)

## Audio Separation Models

- **spleeter:2stems** (default): Vocals and accompaniment separation
- **spleeter:4stems**: 4-stem separation (vocals, drums, bass, other)
- **spleeter:5stems**: 5-stem separation (vocals, drums, bass, piano, other)

## Testing

No formal test suite currently implemented. Manual testing workflow:
1. Test merge operation on sample drama directory
2. Verify audio separation with Spleeter
3. Validate transcoding output quality
