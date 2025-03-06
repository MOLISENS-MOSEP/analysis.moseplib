#!/usr/bin/env python3

"""Fixes the timestamps in a ROS 2 bag metadata file whith multiple subfiles/splits.

_extended_summary_
"""

from pathlib import Path
from moseplib.data.pointcloud_processing import load_pointcloudset


def create_parquet_files(data_dir, bag_names, topics):
    for bag_name in bag_names:
        for topic in topics:
            _ = load_pointcloudset(
                data_dir,
                bag_name,
                topic=topic,
                safe_parquet=True,
                verbose=True,
            )


if __name__ == "__main__":
    # import argparse

    # # Create an ArgumentParser object
    # parser = argparse.ArgumentParser(
    #     description="..."
    # )
    # # Add an argument to the parser
    # parser.add_argument(
    #     "data_dir",
    #     metavar="d",
    #     type=str,
    #     help="Path to the bagfile directory.",
    # )
    # # Parse the command-line arguments
    # args = parser.parse_args()
    # data_dir = args.data_dir

    data_dir = Path("ViF_Roof") / "data"
    bag_names = ["molisens_met_2023_08_07-15_36_45_converted",
                 "molisens_met_2023_08_29-06_04_46_converted"]
    topics = ["/sensing/lidar/points",
              "/sensing/lidar/points2", "/sensing/radar/points"]
    create_parquet_files(data_dir, bag_names=bag_names, topics=topics)
