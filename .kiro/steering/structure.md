# Project Structure

## Directory Layout

```
drama-video-processor/
├── drama_processor/          # Main application package
│   ├── cli.py               # Command-line interface and argument parsing
│   ├── main.py              # Entry point and high-level orchestration
│   ├── orchestrator.py      # Task coordination and batch processing
│   ├── merger.py            # Video merging implementation
│   ├── separator.py         # Audio separation implementation
│   ├── transcoder.py        # Video transcoding implementation
│   ├── subtitle.py          # Subtitle parsing and manipulation
│   ├── ffmpeg_wrapper.py    # FFmpeg command wrapper
│   ├── scanner.py           # Directory structure scanning
│   ├── sorter.py            # File sorting utilities
│   ├── state.py             # Resume state management
│   ├── progress.py          # Progress tracking and callbacks
│   ├── logger.py            # Logging configuration
│   ├── error_handler.py     # Error handling utilities
│   ├── file_manager.py      # File operations and management
│   ├── resource_monitor.py  # System resource monitoring
│   ├── report.py            # Report generation
│   ├── config.py            # Configuration management
│   ├── models.py            # Data classes and enums
│   └── interfaces.py        # Abstract base classes
├── drama/                   # Sample/test drama directories
├── reports/                 # Generated processing reports
├── requirements.txt         # Python dependencies
├── setup.py                # Package installation configuration
└── README.md               # User documentation

## Drama Directory Structure

The tool supports two directory formats:

**Format 1: Direct subdirectories (legacy)**
```
drama/drama-XXXX/
├── video/                   # Video segments
├── srt/                     # Subtitle files
├── merged/                  # Merge output (auto-created)
├── cleared/                 # Separation output (auto-created)
└── encoded/                 # Transcode output (auto-created)
```

**Format 2: Original subdirectory (recommended)**
```
drama/drama-XXXX/
├── original/
│   ├── video/              # Video segments
│   └── srt/                # Subtitle files
├── merged/                 # Merge output (auto-created)
├── cleared/                # Separation output (auto-created)
└── encoded/                # Transcode output (auto-created)
```

## Architecture Patterns

### Module Organization
- **Interfaces** (`interfaces.py`): Abstract base classes define contracts
- **Models** (`models.py`): Dataclasses for type-safe data structures
- **Processors**: Concrete implementations inherit from `VideoProcessor`
- **Orchestrators**: Coordinate multiple processors with different strategies

### Orchestrator Variants
- `Orchestrator`: Base sequential processing
- `ConcurrentOrchestrator`: Thread pool-based parallel processing
- `ResumableOrchestrator`: State management for resume capability
- `ReportingOrchestrator`: Detailed report generation

### Processing Pipeline
1. **Scanner** validates directory structure
2. **Sorter** orders files numerically
3. **Processor** (Merger/Separator/Transcoder) executes operation
4. **FFmpegWrapper** handles video/audio operations
5. **StateManager** tracks completion (if resume enabled)
6. **ReportGenerator** creates processing reports

## Code Conventions

- **Naming**: Chinese docstrings and comments, English code
- **Type hints**: Used throughout for clarity
- **Dataclasses**: Preferred for data structures
- **Enums**: Used for type-safe constants
- **Path objects**: `pathlib.Path` instead of strings
- **Error handling**: Custom exceptions in `error_handler.py`
- **Logging**: Centralized through `ProcessingLogger`

## Configuration Files

- `.drama_processor_state.json`: Resume state (auto-generated)
- `config.json`: Optional user configuration file
- `reports/*.json`: Processing reports with timestamps
