#!/usr/bin/env python3

import io
from pathlib import Path
from PIL import Image
from warnings import warn

import pandas as pd
from rich import print as rprint

from moseplib.data import config, read_rosbag
# if config_variable == "highlevel":
#     from rosbags.highlevel import AnyReader as ReaderClass
# elif config_variable == "rosbag2":
#     from rosbags.rosbag2 import Reader as ReaderClass
# else:
#     raise ValueError("Invalid config variable value")


def load_timeseries(
    data_dir: Path | str | None = None,
    bag_name: str | None = None,
    topics: str | tuple[str, ...] | None = None,
    safe_parquet: None | Path = None,
    force_reload: bool = False,
    verbose: bool = False,
) -> pd.DataFrame | None:
    if safe_parquet is not None:
        if verbose:
            rprint(f"Searching for pointcloudset files in:\n{safe_parquet}")

        if safe_parquet.exists() and not force_reload:
            rprint("Found parquet files, loading timeseries data...")
            return pd.read_parquet(safe_parquet)

        rprint(f"No pointcloudset files found for: {bag_name}.")

    if data_dir is not None and bag_name is not None and topics is not None:
        if isinstance(topics, str):
            topics = (topics,)

        if not (1 <= len(topics) <= 2):
            raise ValueError("topics must be a string or tuple of one or two topic names.")

        data_dir = Path(data_dir)
        bag_path = data_dir / bag_name
        if not bag_path.exists():
            raise FileNotFoundError(f"No pointcloudset files found and {bag_path} does not exist")

        rprint(f"Loading timeseries data from bag file: {bag_path}...")
        df = combine_and_resample_ws_data(bag_path, topics[0], topics[1] if len(topics) == 2 else None)
        if verbose:
            rprint("Loaded data with shape:", df.shape)

        if safe_parquet:
            df.to_parquet(safe_parquet)
        else:
            # Calculate on the fly
            rprint("Loading bag file on the fly..")

        return df
    print("No DataFrame loaded! Either provide safe_parquet or data_dir, bag_name and topics.")


def combine_and_resample_ws_data(bag_path: Path, topic_a: str, topic_b: str | None = None) -> pd.DataFrame:
    df_ws_a = deserialize(
        bag_path,
        topic_a,
        config.PATH_TO_LUFFT_MSGS,
        timestamp_source="msg",
    )
    # Unify timestamp to concat the dataframes
    # Set the ferquency of the index to 1s
    df_ws_a = df_ws_a.resample("1s").nearest()

    # If topic_b is provided, deserialize and resample it as well and combine with df_ws_a
    if topic_b is not None:
        df_ws_b = deserialize(
            bag_path,
            topic_b,
            config.PATH_TO_LUFFT_MSGS,
            timestamp_source="msg",
        )

        df_ws_b = df_ws_b.resample("1s").nearest()
        df = pd.concat([df_ws_a, df_ws_b], axis=1)
    else:
        df = df_ws_a

    # Shift the intensity of the precipitation to the past by 60s to match the rest of the data.
    if "intensity_hour" in df.precipitation.columns:
        df.loc[:, ("precipitation", "intensity_hour_shifted")] = df.precipitation.intensity_hour.shift(
            periods=-60, freq="s"
        )
        df.loc[:, ("precipitation", "intensity_hour_shifted")] = df.loc[
            :, ("precipitation", "intensity_hour_shifted")
        ].fillna(0.0)

    # remove lines with nan
    if df.isna().sum().max() <= 1:
        df = df.dropna()
    else:
        warn(f"Warning: {df.isna().sum().max()} NaN values found in the data. Use df.isna().sum() to see details.")

    return df


def deserialize(
    bag_file: Path,
    topic: str,
    path_to_custom_msgs: Path | None = None,
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
    df = deserialize(
        "/workspaces/MOLISENSext_analysis/data/0external/ubuntu2004_bagfiles/molisens_met_2023_03_07-14_05_21_converted",
        # "/workspaces/MOLISENSext_analysis/data/2interim/bad_aussee/data/molisens_met_2023_04_14-09_23_34_converted",
        "/sensing/aws/ws100_measurements",
        config.PATH_TO_LUFFT_MSGS,
    )
    print(df)
