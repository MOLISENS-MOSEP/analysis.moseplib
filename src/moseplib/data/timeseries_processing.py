#!/usr/bin/env python3

from moseplib.data import config, read_rosbag

import io
import pandas as pd
from pathlib import Path
from PIL import Image

# if config_variable == "highlevel":
#     from rosbags.highlevel import AnyReader as ReaderClass
# elif config_variable == "rosbag2":
#     from rosbags.rosbag2 import Reader as ReaderClass
# else:
#     raise ValueError("Invalid config variable value")


def load(
    bag_file: Path,
    topic: str,
    path_to_custom_msgs: Path = None,
    timestamp_source: str = "header",
    has_header: bool = True,
) -> pd.DataFrame:
    if topic not in read_rosbag.get_topics_of_bagfile(bag_file, verbose=False)["topics"]:
        print(read_rosbag.get_topics_of_bagfile(bag_file, verbose=True))
        raise ValueError(f"Topic {topic} not found in bag file.")

    data, msg_type = read_rosbag.get_data_deserialized(
        bag_file, topic, path_to_custom_msgs, timestamp_source=timestamp_source, has_header=has_header
    )

    if msg_type == "lufft_wsx_interfaces/msg/LufftWSXXX":
        df = pd.DataFrame(data).T
        # Add level names for columns and rows
        df.columns.names = ["Catgegory", "Parameter"]
        df.index.names = ["Timestamp"]
        return df

    elif msg_type == "sensor_msgs/msg/CompressedImage":
        return pd.DataFrame(pd.Series(data), columns=["CompressedImage"])
    else:
        raise ValueError(f"Message type {msg_type} not implemented.")


def compressed_img_to_rgb(jpeg_data):
    # Convert the 1D uint8 array to bytes
    img_bytes = bytes(jpeg_data)

    # Create a BytesIO object and load the image
    img_buffer = io.BytesIO(img_bytes)
    img = Image.open(img_buffer)

    # Convert to RGB if needed (in case it's BGR)
    return img.convert("RGB")


if __name__ == "__main__":
    # print(list(Path(config.PATH_TO_LUFFT_MSGS).glob("**/*")))
    read_rosbag.get_topics_of_bagfile(
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
