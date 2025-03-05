#!/usr/bin/env python3

from tqdm.auto import tqdm
from pathlib import Path
from rich import print


from pointcloudset import Dataset
from . import config


def extract(bag_file: Path, topics: list, verbose: bool = False) -> None:
    """
    Extracts point clouds from a ROS bag file.

    Args:
        bag_file: The path to the ROS bag file to extract point clouds from.
        topics: A list of ROS topics to extract point clouds from.
        verbose: If True, print progress messages to the console. Default is False.

    Returns:
        None

    Raises:
        ValueError: If the input bag file does not exist.

    Notes:
        This function uses the `rosbag` library to extract point clouds from a ROS bag file.
        The extracted point clouds are saved to disk as `.ply` files in the same directory as the input bag file.
    """

    bag_file = Path(bag_file)
    if not bag_file.exists():
        raise ValueError(f"{bag_file} does not exist")

    def extract_topic(bag_file: Path, topic: str, verbose=verbose) -> None:
        if verbose:
            print(f"Extracting {topic}...")
        dataset = Dataset.from_file(bag_file, topic=topic, keep_zeros=False)
        if verbose:
            print(f"Dataset loaded with len: {len(dataset)}")
            print("Writing to file...")
        dataset.to_file(
            Path(bag_file.parent / "pointcloudset" / topic[1:].replace("/", "_")),
            use_orig_filename=True,
        )

    for topic in tqdm(topics):
        extract_topic(bag_file, topic, verbose=verbose)


if __name__ == "__main__":
    import argparse

    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="Process path to bagfile and topics to extract.")
    # Add an argument to the parser
    parser.add_argument(
        "path",
        metavar="P",
        type=str,
        help="Path to the bagfile directory to extract point clouds from.",
    )
    parser.add_argument(
        "--topics",
        metavar="T",
        type=str,
        nargs="+",
        help="A list of topics to extract from the bagfile",
    )
    # Parse the command-line arguments
    args = parser.parse_args()
    path = args.path
    topics = args.topics

    topics = config.PC_TOPICS if topics is None else topics

    extract(
        path,
        topics=topics,
        verbose=True,
    )
