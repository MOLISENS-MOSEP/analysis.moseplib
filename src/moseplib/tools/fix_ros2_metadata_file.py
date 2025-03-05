#!/usr/bin/env python3

"""Fixes the timestamps in a ROS 2 bag metadata file whith multiple subfiles/splits.

_extended_summary_
"""

from pathlib import Path
import shutil
import yaml


def load_yaml_file(path: Path) -> dict:
    """Loads a yaml file and returns its contents as a dictionary.

    Args:
        path (Path): The path to the yaml file.

    Returns:
        dict: The contents of the yaml file as a dictionary.
    """

    with open(path, "r") as f:
        return yaml.load(f, Loader=yaml.SafeLoader)


def save_yaml_file(path: Path, data: dict) -> None:
    """Saves a dictionary to a yaml file.

    Args:
        path (Path): The path to the yaml file.
        data (dict): The data to save to the yaml file.

    Returns:
        None
    """

    with open(path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=float("inf"),
        )


def fix_timestamp_order(bag_path: Path):
    """Fixes the timestamp order in the metadata file of a ROS2 bagfile.

    Checks if the bagfile has multiple subfiles/splits. If it does, copies the original metadata file to a backup file.
    Calculates the correct starting time, duration, and message count for the bagfile based on the subfiles/splits.
    If the starting time, duration, or message count in the metadata file is incorrect, updates the metadata file with
    the correct values. Saves the updated metadata file to disk.

    Args:
        bag_path (Path): The path to the bagfile.

    Returns:
        None

    Raises:
        None
    """

    bag_path = Path(bag_path)
    metadata_path = bag_path / "metadata.yaml"
    metadata_backup_file = metadata_path.parent / "metadata_original.yaml"

    # Check if bagfile has multiple subfiles/splits.
    metadata = load_yaml_file(metadata_path)
    if len(metadata["rosbag2_bagfile_information"]["files"]) == 1:
        return

    # copy original metadata file
    if not metadata_backup_file.exists():
        shutil.copyfile(metadata_path, metadata_backup_file)

    # fmt: off
    start_time =    metadata['rosbag2_bagfile_information']['starting_time']['nanoseconds_since_epoch']
    duration =      metadata['rosbag2_bagfile_information']['duration']['nanoseconds']
    message_count = metadata['rosbag2_bagfile_information']['message_count']

    start_time_first_file = metadata['rosbag2_bagfile_information']['files'][0] \
        ['starting_time']['nanoseconds_since_epoch']

    duration_all_files = 0
    message_count_all_files = 0
    for file in metadata["rosbag2_bagfile_information"]["files"]:
        duration_all_files += file["duration"]["nanoseconds"]
        message_count_all_files += file["message_count"]

    if start_time_first_file != start_time:
        metadata["rosbag2_bagfile_information"]["starting_time"]['nanoseconds_since_epoch'] = start_time_first_file

    if duration_all_files != duration:
        metadata["rosbag2_bagfile_information"]["duration"]['nanoseconds'] = duration_all_files

    if message_count_all_files != message_count:
        metadata["rosbag2_bagfile_information"]["message_count"] = message_count_all_files

    save_yaml_file(metadata_path, metadata)
    # fmt: on


if __name__ == "__main__":
    import argparse

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="Fix timestamps in a ROS 2 bag metadata file with multiple subfiles/splits."
    )
    # Add an argument to the parser
    parser.add_argument(
        "path",
        metavar="P",
        type=str,
        help="Path to the bagfile directory to fix timestamps in.",
    )
    # Parse the command-line arguments
    args = parser.parse_args()
    path = args.path

    fix_timestamp_order(path)
