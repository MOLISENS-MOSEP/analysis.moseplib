#!/usr/bin/python3

import argparse
from pathlib import Path
from typing import List, Tuple, Union, Dict
import yaml

import frontmatter
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
import pandas as pd
from rich import print as rprint
from rich.progress import track

from moseplib.tools.fix_ros2_metadata_file import fix_timestamp_order
from moseplib.data import timeseries_processing, config, read_rosbag


# * Note that multiple metadata concepts appear in this script:
# * - First, there is the metadata that is extracted from the bagfile itself in this script containing the met data.
# * - Second, there is the metadata file that is created by ROS2 when a bagfile is recorded.
# * - Third, the Ouster sensor has its own metadata file that is stored in the bagfile usually named:
# *   ouster_metadata.txt.


def get_total_mcap_size(directory):
    directory_path = Path(directory)
    total_size = sum(f.stat().st_size for f in directory_path.glob("*.mcap"))

    if total_size >= 1024 * 1024 * 1024:  # size is in GB
        return f"{total_size / (1024 * 1024 * 1024):.2f} GB"
    elif total_size >= 1024 * 1024:  # size is in MB
        return f"{total_size / (1024 * 1024):.2f} MB"
    else:  # size is in bytes
        return f"{total_size} bytes"


def extract_metadata(bag_path: Union[str, Path]) -> dict[str, object]:
    """
    Extracts metadata from a ROS bag file and creates a precipitation plot.

    Parameters:
        bag_path (Union[str, Path]): The path to the ROS bag file.

    Returns:
        tuple: A tuple containing the metadata dictionary and the figure object.

    Raises:
        ValueError: If the bag file does not contain the required topics.

    Example:
        meta, fig = extract_metadata("path/to/bagfile.bag")
    """

    bag_path = Path(bag_path)
    meta: dict[str, object] = {"note_type": "measurement", "bag_size": get_total_mcap_size(bag_path)}

    df = timeseries_processing.deserialize(bag_path, "/sensing/aws/ws100_measurements", config.PATH_TO_LUFFT_MSGS)
    precip_stats = {
        "min": df.precipitation.intensity_hour.min(),
        "max": df.precipitation.intensity_hour.max(),
        "mean": float(df.precipitation.intensity_hour.mean()),
        "std": df.precipitation.intensity_hour.std(),
    }
    meta["precipitation_intensity_hour"] = precip_stats

    # Get the topics and additional metadata form bagfile
    topics = read_rosbag.get_topics_of_bagfile(bag_path, verbose=False)
    # Stringify the datetime objects
    topics["start_time"] = topics["start_time"].strftime("%Y-%m-%d %H:%M:%S")
    topics["end_time"] = topics["end_time"].strftime("%Y-%m-%d %H:%M:%S")
    topics["duration"] = str(topics["duration"])

    meta.update(topics)
    # Add a empty comment field
    meta["comment"] = ""

    return meta


def plot_precipitation_data(bag_path: Union[str, Path]) -> Figure:
    bag_path = Path(bag_path)
    df = timeseries_processing.deserialize(bag_path, "/sensing/aws/ws100_measurements", config.PATH_TO_LUFFT_MSGS)
    fig = plt.figure(figsize=(12, 20))
    plot_data = df.precipitation.loc[:, "absolute":"hail_particles"]
    axs = plot_data.plot(
        subplots=True,
        figsize=(12, 20),
        grid=True,
        fontsize=18,
        sharex=True,
        ax=fig.subplots(len(plot_data.columns), 1),
    )
    plt.tight_layout()

    return fig


def save_dict_to_markdown(data_dict: dict, output_path: Union[str, Path], overwrite: str | bool = False) -> None:
    """
    Saves a dictionary to a Markdown file.

    Parameters:
        data_dict (dict): The dictionary to save.
        output_path (Union[str, Path]): The path to the output Markdown file.
        overwrite (bool): Whether to overwrite the output file if it already exists. Default is False.

    Returns:
        None

    Raises:
        FileExistsError: If the output file already exists and overwrite is False.

    Example:
        save_dict_to_markdown({"key": "value"}, "output.md")
    """
    output_file = Path(output_path)
    if output_file.exists() and not overwrite:
        raise FileExistsError(f"{output_file} already exists. Use --overwrite to overwrite it.")

    with output_file.open("w") as f:
        # Use pprint to pretty-print the dictionary to a string
        # pretty_dict = pprint(data_dict)
        f.write("---\n")
        yaml.dump(data_dict, f, sort_keys=False)
        f.write("---\n\n")


def add_image_to_markdown(
    plot: plt.Figure,
    markdown_path: Union[str, Path],
    plot_path: Union[str, Path],
    title: str = "# Precipitation plot\n",
) -> None:
    markdown_path = Path(markdown_path)
    plot_path = Path(plot_path)

    rel_image_path = plot_path.relative_to(markdown_path.parent)
    # Save the plot to file
    plot.savefig(plot_path)

    mode = "a" if markdown_path.exists() else "w"
    with markdown_path.open(mode) as f:
        # Add an image to the output file
        f.write(title)
        f.write(f"\n![precipitation_plot]({rel_image_path})\n")


def create_overview_table(
    markdown_files: Dict[str, Union[str, Path]],
    sort_by: Union[str, List[str]],
    ascending: Union[bool, List[bool]] = False,
) -> str:
    """
    Creates a table with metadata from the frontmatter section of multiple Markdown files.

    Parameters:
        markdown_files (List[str]): A list of paths to the Markdown files.
        sort_by (Union[str, List[str]]): The column to sort the table by. Default is "precipitation_intensity_hour.max".
        ascending (bool): Whether to sort the table in ascending order. Default is False.

    Returns:
        str: The Markdown table as a string.

    Example:
        table_str = create_metadata_table(["file1.md", "file2.md"], sort_by="start_time", ascending=True)
    """
    # Create an empty DataFrame to hold the metadata
    metadata_list = []

    # Loop through the Markdown files and extract the metadata
    for name, file_path in markdown_files.items():
        file_path = Path(file_path)
        if not frontmatter.check(file_path):
            rprint(f"No frontmatter found in file {file_path}")
            continue
        with open(file_path, "r") as f:
            # Use frontmatter to extract the metadata from the frontmatter section
            post = frontmatter.load(f)

        # Add the metadata to the DataFrame
        metadata_list.append(
            {
                "bagfile": name,
                "precipitation_intensity_hour.max": post.metadata["precipitation_intensity_hour"]["max"],
                "start_time": pd.to_datetime(post.metadata["start_time"]),
                "duration": pd.Timedelta(post.metadata["duration"]),
                "bag_size": post.metadata["bag_size"],
                "comment": post.metadata["comment"],
            }
        )

    # Sort the DataFrame by the specified column
    metadata_df = pd.DataFrame(metadata_list).sort_values(by=sort_by, ascending=ascending)

    # Convert the DataFrame to a Markdown table
    table_str = metadata_df.to_markdown(index=True)

    return table_str


def main(
    path: Union[str, Path],
    output: Union[str, Path],
    repair: bool,
    overwrite: bool,
    img_subdir: Union[str, Path],
    entry: dict = None,
    create_overview: bool = False,
):
    path = Path(path)

    rprint("Looping through all bagfiles in directory...")
    output_paths = {}
    for bag_path in track(list(path.iterdir()), description="Processing bagfiles..."):
        # Ignore files, only process directories
        if bag_path.is_file():
            continue
        if repair:
            rprint(f"Repairing {bag_path}/metadata.yaml")
            fix_timestamp_order(bag_path)

        meta = extract_metadata(bag_path)
        precip_plot = plot_precipitation_data(bag_path)

        # Add an optional dictionary to also include in the metadata file. Default is None.
        if entry:
            # If entry is a path to a yaml file, load it.
            if not isinstance(entry, dict):
                with open(entry, "r") as stream:
                    entry = yaml.safe_load(stream)

            # Make sure that sensor data from entry is at top of dict.
            temp_dict = meta
            meta = {"sensor_setup": entry}
            meta.update(temp_dict)

        plot_suffix = "precipitation_plot.png"
        if not output:
            output_path = bag_path / "met_metadata.md"
            plot_name = f"{plot_suffix}"
        else:
            output_path = Path(output) / f"{bag_path.name}_met_metadata.md"
            plot_name = f"{bag_path.name}_{plot_suffix}"

        if img_subdir:
            img_dir = output_path.parent / img_subdir
            img_dir.mkdir(exist_ok=True)
        else:
            img_dir = output_path.parent

        img_path = img_dir / plot_name

        save_dict_to_markdown(meta, output_path, overwrite=overwrite)
        add_image_to_markdown(precip_plot, output_path, plot_path=img_path)

        output_paths[bag_path.name] = output_path

    if create_overview:
        rprint(f"Creating overview table at {path}/overview.md")
        table = create_overview_table(
            output_paths, sort_by=["precipitation_intensity_hour.max", "start_time"], ascending=[False, True]
        )
        with open(path / "met_overview_table.md", "w") as f:
            f.write(table)


def arg_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to bag file (the folder containing individual files).")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Directory where to store markdown files. If None is given, the Markdown is created inside the bagfile "
            "folder."
        ),
    )
    parser.add_argument(
        "-p",
        "--repair",
        action="store_true",
        help="Wheather to repair ROS2 bagfile metadata files",
    )
    parser.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        help="Weather to overwrite existing markdown files.",
    )
    parser.add_argument(
        "-c",
        "--create_overview",
        action="store_true",
        help="Weather to create a markdown file containing a overview of all created markdowns at the [path] location.",
    )
    parser.add_argument(
        "-s",
        "--img_subdir",
        type=str,
        help=(
            "If given, the image is stored in a subdirectory. In combination with output this helps to store the"
            "images in a separate folder."
        ),
    )
    parser.add_argument(
        "-e", "--entry", type=yaml.safe_load, help="Add additional entries to the metadata file as json dict."
    )

    args = parser.parse_args()
    main(
        path=args.path,
        output=args.output,
        repair=args.repair,
        overwrite=args.overwrite,
        create_overview=args.create_overview,
        img_subdir=args.img_subdir,
        entry=args.entry,
    )


if __name__ == "__main__":
    arg_main()

    # python src/data/get_metadata_from_bagfile/get_metadata_from_bagfiles.py data/1raw/datasets/ViF_Roof/2023_08_29 -pwc -o data/1raw/datasets/ViF_Roof/report -s attachments -e src/data/get_metadata_from_bagfile/sensor_setup.yaml
