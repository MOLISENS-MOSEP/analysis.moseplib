# moseplib

Core Python library for reading, processing, and analyzing sensor data from the MOSEP (Modular Hardware and Software System for Multi-Sensor Environment Perception) measurement setup. Provides tools to extract point cloud and weather station data from ROS2 bag files and convert them into analysis-ready formats.

## Features

- **ROS2 bag file reading** — Extract point cloud (LiDAR/radar) and weather station data from `.mcap` bag files, including support for custom Lufft WSX weather station message types.
- **Point cloud processing** — Convert raw point clouds to [`pointcloudset`](https://github.com/virtual-vehicle/pointcloudset) datasets stored as Parquet files. Resample, subset, and aggregate by configurable time periods and spatial regions.
- **Weather time series** — Deserialize Lufft weather station messages into structured pandas DataFrames with multi-level columns (category × parameter). Resample and combine data from multiple weather stations.
- **Spatial filtering** — `Limits` utility for defining 3D bounding boxes and applying inclusion/exclusion filters to point cloud data.
- **Statistics** — Per-frame point cloud statistics (point count, mean/sum intensity).
- **Metadata extraction** — CLI tool to extract bag file metadata (topics, duration, precipitation stats) and generate Markdown reports with embedded precipitation plots.
- **Image extraction** — Decode `CompressedImage` messages from bag files to RGB images.

## Installation

Requires Python ≥ 3.9, < 3.12.

```bash
pip install moseplib
```

Or as part of the `mosep-analysis` workspace (recommended):

```bash
# From the mosep-analysis root
uv sync
```

## CLI

### `extract_metadata`

Extract metadata and precipitation plots from ROS2 bag files:

```bash
extract_metadata <path_to_bagfile> [--output_dir <dir>]
```

Generates a Markdown file with YAML frontmatter containing bag metadata (topics, timestamps, duration, precipitation statistics) and an embedded precipitation plot.

## Package Structure

```
src/moseplib/
├── cli/
│   ├── get_metadata_from_bagfiles.py   <- extract_metadata CLI entry point
│   └── sensor_setup.yaml              <- Sensor configuration (Ouster LiDAR, Smartmicro radar)
├── config/
│   ├── precipitation_codes.py          <- WMO Synop Code 4680 weather type definitions
│   └── custom_ros_msgs/
│       └── lufft_wsx_interfaces/msg/   <- Custom ROS2 message definitions for Lufft weather station
├── data/
│   ├── config.py                       <- Package-level config (topics, field names, paths)
│   ├── utils.py                        <- Limits (3D bounding box), spatial filtering utilities
│   ├── read_rosbag.py                  <- ROS2 bag file reading and message deserialization
│   ├── pointcloud_processing.py        <- Point cloud extraction, loading, resampling, aggregation
│   ├── timeseries_processing.py        <- Weather time series loading, deserialization, resampling
│   ├── pc_statistics.py                <- Point cloud statistics (n_points, mean/sum intensity)
│   └── extract_pcs_from_bagfile.py     <- Standalone script for batch point cloud extraction
└── tools/
    ├── fix_ros2_metadata_file.py       <- Fix timestamp ordering in ROS2 bag metadata files
    └── create_parquet_files_from_pc.py <- Batch convert bag files to parquet
```

## Supported Sensors

| Sensor | Type | Details |
|---|---|---|
| Ouster OS-1-64-U02 | LiDAR | 1024×10 mode, RNG19_RFL8_SIG16_NIR16_DUAL profile |
| Smartmicro UMRR-11 Type 132 | Radar | — |
| Lufft WSX-series | Weather station | Temperature, humidity, wind, precipitation, radiation, air pressure |

## Dependencies

- `pandas` — DataFrames and time series
- `pointcloudset` — Point cloud dataset management
- `rosbags` — ROS2 bag file reading
- `pyarrow` — Parquet I/O
- `rich` — Terminal output formatting
- `tqdm` — Progress bars
- `kaleido` — Static image export for Plotly figures
