#!/usr/bin/env python3

from moseplib.data import config
from moseplib.data.pointcloud_processing import extract_pc_from_bagfile


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

    extract_pc_from_bagfile(
        path,
        topics=topics,
        verbose=True,
    )
