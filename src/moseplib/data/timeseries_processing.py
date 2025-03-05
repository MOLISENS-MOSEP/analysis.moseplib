#!/usr/bin/env python3

from src.data import config


from rich import print as rprint
from rich.table import Table
import pandas as pd
from rich.pretty import pprint
from pathlib import Path

# if config_variable == "highlevel":
#     from rosbags.highlevel import AnyReader as ReaderClass
# elif config_variable == "rosbag2":
#     from rosbags.rosbag2 import Reader as ReaderClass
# else:
#     raise ValueError("Invalid config variable value")


from rosbags.typesys import get_types_from_msg, register_types
from rosbags.rosbag2 import Reader

# from rosbags.highlevel import AnyReader as Reader
from rosbags.serde import deserialize_cdr


def guess_msgtype(path: Path) -> str:
    """
    Guesses the message type based on the file path.

    Args:
        path (Path): The path to the file.

    Returns:
        str: The guessed message type.
    """
    name = path.relative_to(path.parents[2]).with_suffix("")
    if "msg" not in name.parts:
        name = name.parent / "msg" / name.name
    return str(name)


def register_custom_ros_msgs(path_to_msgs, verbose=False):
    add_types = {}

    for pathstr in Path(path_to_msgs).glob("**/*"):
        msgpath = Path(pathstr)
        msgdef = msgpath.read_text(encoding="utf-8")
        add_types.update(get_types_from_msg(msgdef, guess_msgtype(msgpath)))

    register_types(add_types)

    try:
        from rosbags.typesys.types import (
            lufft_wsx_interfaces__msg__LufftWSXXX as LufftWSXXX,
        )

    except ImportError:
        print("Could not import custom message types. Please check your ROS installation.")

    if verbose:
        from pydoc import render_doc

        rprint(render_doc(LufftWSXXX))


def get_topics_of_bagfile(bag_file, verbose=True):
    # Crete output table
    table = Table(title="Content of bag file")
    table.add_column("Topic", style="cyan")
    table.add_column("MSG", style="magenta")

    # create reader instance and open for reading
    metadata = {}
    with Reader(bag_file) as reader:
        # topic and msgtype information is available on .connections list
        metadata["topics"] = {}
        for connection in reader.connections:
            table.add_row(connection.topic, connection.msgtype)
            metadata["topics"][connection.topic] = str(connection.msgtype)

        metadata["compression_format"] = reader.compression_format
        metadata["compression_mode"] = reader.compression_mode
        metadata["custom_data"] = reader.custom_data
        metadata["start_time"] = pd.to_datetime(reader.start_time, unit="ns", origin="unix")
        metadata["end_time"] = pd.to_datetime(reader.end_time, unit="ns", origin="unix")
        metadata["duration"] = pd.to_timedelta(reader.duration, unit="ns")
        # metadata["files"] = reader.files
        metadata["message_count"] = {}
        metadata["message_count"]["total"] = reader.message_count
        # This is simply the content of the metadata.yaml file
        # Could be used for restoring the metadata.yaml file but not needed here.
        # metadata["metadata"] = reader.metadata

        for topic in reader.metadata["topics_with_message_count"]:
            metadata["message_count"][topic["topic_metadata"]["name"]] = topic["message_count"]

    if verbose:
        rprint(table)

    return metadata


def msg_decoder(msg):
    """Extracts data from a ROS message.

    Args:
        msg: ROS message whose data will be extracted.

    Returns:
        Dictionary whose keys are tuples of the form (msg_type, measurement_name) and whose values are the value of the measurement in that message.
    """
    msg_data = {}
    for msg_type, msg_content in msg.__dict__.items():
        # Exclude header and __msgtype__ fields as they are special fields
        if msg_type == "header" or msg_type == "__msgtype__":
            continue

        # msg_data[field_name] = {}
        for field, value in msg_content.__dict__.items():
            if field == "__msgtype__":
                continue

            if field.endswith("_valid") and value == True:
                measurement_name = field.rsplit("_", 1)[0]
                msg_data[(msg_type, measurement_name)] = getattr(msg_content, measurement_name)

    return msg_data


def _get_data(bag_file: Path, topic: str) -> list:
    """WIP"""
    data = []
    with Reader(bag_file) as reader:
        connections = [x for x in reader.connections if x.topic == topic]
        i = 0
        for connection, timestamp, rawdata in reader.messages(connections=connections):
            data.append(rawdata)
            i += 1
            if i > 100:
                break

    return data


def get_data_deserialized(
    bag_file: Path,
    topic: str,
    path_to_custom_msgs: Path = None,
    timestamp_source: str = "header",
    has_header: bool = True,
) -> dict:
    if path_to_custom_msgs:
        register_custom_ros_msgs(path_to_custom_msgs, verbose=False)

    data = {}

    with Reader(bag_file) as reader:
        connections = [x for x in reader.connections if x.topic == topic]
        for connection, timestamp_msg, rawdata in reader.messages(connections=connections):
            try:
                msg = deserialize_cdr(rawdata, connection.msgtype)
            except KeyError as e:
                raise KeyError(
                    f"Could not deserialize message: {e}. Include the path to the custom messages (path_to_custom_msgs)."
                ) from e
            # print(msg.header.frame_id)

            if timestamp_source == "msg":
                timestamp = pd.to_datetime(timestamp_msg, unit="ns", origin="unix")
            if timestamp_source == "header":
                timestamp = pd.to_datetime(
                    msg.header.stamp.sec * 1e9 + msg.header.stamp.nanosec,
                    unit="ns",
                    origin="unix",
                )

            if has_header:
                data[timestamp] = msg_decoder(msg)
            else:
                data[timestamp] = msg
    return data


def load(
    bag_file: Path,
    topic: str,
    path_to_custom_msgs: Path = None,
    timestamp_source: str = "header",
) -> pd.DataFrame:
    if topic not in get_topics_of_bagfile(bag_file, verbose=False)["topics"]:
        print(get_topics_of_bagfile(bag_file, verbose=True))
        raise ValueError(f"Topic {topic} not found in bag file.")

    data = get_data_deserialized(bag_file, topic, path_to_custom_msgs, timestamp_source=timestamp_source)
    df = pd.DataFrame(data).T
    # Add level names for columns and rows
    df.columns.names = ["Catgegory", "Parameter"]
    df.index.names = ["Timestamp"]
    return df


if __name__ == "__main__":
    # print(list(Path(config.PATH_TO_LUFFT_MSGS).glob("**/*")))
    get_topics_of_bagfile(
        "/workspaces/MOLISENSext_analysis/data/0external/ubuntu2004_bagfiles/molisens_met_2023_03_07-14_05_21_converted"
    )
    # register_custom_ros_msgs(config.PATH_TO_LUFFT_MSGS, verbose=False)
    df = load(
        "/workspaces/MOLISENSext_analysis/data/0external/ubuntu2004_bagfiles/molisens_met_2023_03_07-14_05_21_converted",
        # "/workspaces/MOLISENSext_analysis/data/2interim/bad_aussee/data/molisens_met_2023_04_14-09_23_34_converted",
        "/sensing/aws/ws100_measurements",
        config.PATH_TO_LUFFT_MSGS,
    )
    print(df)
