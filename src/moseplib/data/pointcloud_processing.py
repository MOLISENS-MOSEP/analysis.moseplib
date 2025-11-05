#!/usr/bin/env python3

# from src.data import config

from pathlib import Path
from typing import Callable
import warnings

from dask import delayed, compute
import pandas as pd
from pointcloudset import Dataset, PointCloud
from pointcloudset.pipeline.delayed_result import DelayedResult
from rich import print as rprint
from tqdm import tqdm

from moseplib.data.utils import Limits


def print_stats(bag_path, dataset):
    freq = len(dataset) / (dataset.duration.seconds + dataset.duration.microseconds / 1e6)

    rprint(
        f"Dataset loaded from:\n{bag_path}\n\n",
        f"start =    {dataset.start_time}\n",
        f"end =      {dataset.end_time}\n",
        f"duration = {dataset.duration}\n",
        f"length =   {len(dataset)}\n",
        f"avg frequency =  {freq:.2f} Hz",
    )


def extract_pc_from_bagfile(bag_file: Path, topics: list, verbose: bool = False) -> None:
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
            rprint(f"Extracting {topic}...")
        dataset = Dataset.from_file(bag_file, topic=topic, keep_zeros=False)
        if verbose:
            rprint(f"Dataset loaded with len: {len(dataset)}")
            rprint("Writing to file...")
        dataset.to_file(
            Path(bag_file.parent / "pointcloudset" / topic[1:].replace("/", "_")),
            use_orig_filename=True,
        )

    for topic in tqdm(topics):
        extract_topic(bag_file, topic, verbose=verbose)


def load_pointcloudset(
    data_dir: Path,
    bag_name: str,
    topic: str,
    safe_parquet: bool = True,
    keep_zeros: bool = False,
    invert_axes: list[str] | None = None,
    skip_initial_frames: int = 0,
    verbose: bool = False,
) -> Dataset | DelayedResult:
    """
    Load a point cloud dataset from a ROS bag file.

    Args:
        data_dir (Path): Path to the directory containing the bag file and/or pointcloudset files.
        bag_name (str): Name of the ROS bag file to load.
        topic (str): Name of the ROS topic containing to load.
        safe_parquet (bool, optional): Whether to store pre-generated point cloud dataset files in Parquet format if
            available. Defaults to True.
        keep_zeros (bool, optional): Whether to keep points with zero coordinates. Defaults to False.
        invert_axes (list, optional): List of axes to invert (Multiply by -1). Defaults to None.
        skip_initial_frames (int, optional): Number of initial frames to skip in the dataset. Useful for ignoring
            startup transients. Defaults to 0.
        verbose (bool, optional): Whether to print verbose output. Defaults to False.

    Returns:
        Dataset: A point cloud dataset object.

    Raises:
        FileNotFoundError: If no point cloud dataset files are found and the ROS bag file does not exist.
    """
    data_dir = Path(data_dir)
    bag_path = data_dir / bag_name

    pointcloudset_path = data_dir / "pointcloudset" / topic[1:].replace("/", "_") / bag_name
    if verbose:
        rprint(f"Searching for pointcloudset files in:\n{pointcloudset_path}")

    if not pointcloudset_path.exists():
        rprint(f"No pointcloudset files found for topic: {topic}.")

        if not bag_path.exists():
            raise FileNotFoundError(f"No pointcloudset files found and {bag_path} does not exist")

        if not safe_parquet:
            # Calculate on the fly
            rprint("Loading bag file on the fly..")
            dataset = Dataset.from_file(
                bag_path,
                topic=topic,
                keep_zeros=keep_zeros,
            )
            if verbose:
                print_stats(bag_path, dataset)
            return dataset

        rprint("Creating pointcloudset files now..")
        extract_pc_from_bagfile(bag_path, [topic], verbose=verbose)

    dataset = Dataset.from_file(pointcloudset_path)
    if verbose:
        print_stats(pointcloudset_path, dataset)

    if invert_axes:
        if not isinstance(invert_axes, list):
            raise TypeError("invert_axes must be a list")
        if isinstance(dataset, Dataset):
            missing_axis = [elem for elem in invert_axes if elem not in dataset.daskdataframe.columns]
            if missing_axis:
                raise ValueError(f"These axis are not in present in dataset: {missing_axis}")
            rprint("Inverting axes:", invert_axes)
            dataset = dataset.apply(_invert_axes, axes=invert_axes)  # type: ignore
        else:
            warnings.warn("invert_axes is ignored for delayed datasets. Compute the dataset first to use invert_axes.")

    return dataset[skip_initial_frames:]


def _invert_axes(frame: PointCloud, axes: list[str]) -> PointCloud:
    """Helper function to invert the values of the specified axes in a PointCloud.



    Args:
        frame (PointCloud): A pointclouset PointCloud object.
        axes (list[str]): Columns to invert.

    Returns:
        PointCloud: The inverted PointCloud.
    """
    df = frame.data
    df = df.assign(**{axis: -df[axis] for axis in axes})
    return PointCloud(df)


def get_dataset_statistics(dataset: Dataset):
    pass


def _change_dtypes(pc: PointCloud) -> PointCloud:
    """Change dtypes of certain columns to avoid issues during resampling. Especially for 'sum' aggregation"""
    dtype_mappings = {
        "intensity": "float64",
        "reflectivity": "uint64",
        "ambient": "uint64",
    }
    for field, new_dtype in dtype_mappings.items():
        if field in pc.data.columns:
            pc.data[field] = pc.data[field].astype(new_dtype)
    return pc


def _drop_t(pc: PointCloud) -> PointCloud:
    """Drop the 't' column from a PointCloud if it exists as it makes no sense in a resampled context."""
    if "t" in pc.data.columns:
        pc.data = pc.data.drop(columns=["t"])
    return pc


def resample_dataset(ds: Dataset, resampling_period: str, extra_statistics: list | None = None) -> dict[str, Dataset]:
    """Resample a dataset to a given period and calculate statistics for each resampled point cloud.

    Args:
        ds (Dataset): A pointcloudset Dataset object.
        resampling_period (str): A string representing the resampling period as used by Pandas (e.g. "1s").
        statistics (list, optional): A list of statistics to be used for aggregating the resampled datasets (as
            supported by Pandas). Mean is always calculated. Defaults to None.

    Raises:
        ValueError: If timestamps are not monotonically increasing.

    Returns:
        dict[Dataset]: A dictionary containing the resampled datasets for each statistic.
    """
    # prepare dataset by changing dtypes and dropping t column
    ds = ds.apply(_change_dtypes).apply(_drop_t)

    # Ensure that mean is always calculated. Necessary for positioning aggregated points in space (  x, y, z values).
    statistics = ["mean"]
    if extra_statistics is not None:
        statistics.extend(extra_statistics)
    # Check if timestamps are monotonically increasing
    if not pd.Series(ds.timestamps).is_monotonic_increasing:
        raise ValueError("Timestamps are not monotonically increasing. This is a prerequisite for resampling.")

    # Resample the timestampas of the dataset and get indices of the PointClouds to aggregate
    agg_inds = (
        pd.DataFrame({"pc_index": range(len(ds.timestamps))}, index=pd.DatetimeIndex(ds.timestamps))
        .resample(resampling_period)
        .agg(["first", "last"])
    )

    ds_resampled = {key: [] for key in statistics}

    # Loop over indices
    for ts, ind in tqdm(agg_inds.iterrows(), total=len(agg_inds)):
        # Retrieve a subset of the dataset corresponding to the resampled timestamp
        # Maybe use timestamps instead of indices (.get_pointclouds_between_timestamps)
        sub_ds = ds[ind["pc_index", "first"] : ind["pc_index", "last"] + 1]
        # Aggregate PointClouds in the subset
        df_all_stats = sub_ds.agg(statistics, "point")  # type: ignore

        # Retrive the mean x, y, z, range, ring values to be used in all Datasets (i.e. sum and std make no sense)
        xyz = df_all_stats.loc(axis=1)[["x", "y", "z", "range", "ring"], "mean"]
        xyz.columns = xyz.columns.droplevel(1)

        # Create a DataFrame for each statistic
        for stat in statistics:
            df = df_all_stats.xs(stat, level=1, axis=1, drop_level=True)
            # Update the DataFrame with the mean x, y, z values
            df.update(xyz)
            # concatenate the N and original_id columns
            df = pd.concat([df, df_all_stats.N, df_all_stats.original_id], axis=1)
            # Convert to PointCloud and append to the list
            df.reset_index(inplace=True)  # added to account for breaking change in pointcloudset > 0.9.0.
            ds_resampled[stat].append(PointCloud(df, timestamp=ts))  # type: ignore

    return {key: Dataset.from_instance("pointclouds", value) for key, value in ds_resampled.items()}


def subset_and_aggregate_dataset(
    dataset: Dataset, splits: dict[str, dict[str, Limits]], agg_func: Callable | None = None, return_type: str = "dict"
) -> dict | pd.DataFrame | None:
    """
    Aggregates a dataset of point clouds into a single DataFrame.

    This function applies a given aggregation function to subsets of each point cloud in the dataset, defined by the
    limits dictionary. The results are then aggregated either in a dictionary or a DataFrame, depending on the
    `return_type` parameter and the aggregation function `agg_func`.

    Args:
        dataset (pointcloudset.Dataset): The input dataset of point clouds.
        limits_dict (dict[dict]): A dictionary defining the limits for subsets. The keys should be subset names and the
            values should be dictionaries mapping column names to limit objects.
        agg_func (callable): An aggregation function to apply to each subset in the point clouds. This function should
            take a pandas Series as input and return a single value.
        return_type (str, optional): The type of the output. If "dict", the function returns a dictionary. If "df", the
            function returns a DataFrame. Defaults to "dict".

    Returns:
        dict or pd.DataFrame: The aggregated data, either in a dictionary or a DataFrame, depending on the `return_type`
            parameter. Each subset is a column and each timestamp (point cloud from the dataset) is a row.
    """

    def _depth(d):
        if isinstance(d, dict):
            return 1 + (max(map(_depth, d.values())) if d else 0)
        return 0

    result_dict = {}

    if _depth(splits) == 1:
        for target_name, target_limits in splits.items():
            rd = dataset.apply(target_limits.apply_limits)  # type: ignore
            if agg_func:
                rd = pd.concat(rd.apply(agg_func))  # type: ignore
            result_dict[target_name] = rd

        if not agg_func or return_type == "dict":
            return result_dict
        elif return_type == "df":
            return pd.DataFrame(result_dict)

    elif _depth(splits) == 2:
        for target_name, color_dict in splits.items():
            result_dict[target_name] = {}
            for col, target_limits in color_dict.items():
                with warnings.catch_warnings(record=True):
                    rd = dataset.apply(target_limits.apply_limits)
                    if agg_func:
                        rd = pd.concat(rd.apply(agg_func))  # type: ignore
                    result_dict[target_name][col] = rd

        if not agg_func or return_type == "dict":
            return result_dict
        elif return_type == "df":
            return pd.concat(
                [pd.DataFrame(v) for v in result_dict.values()],
                axis=1,
                keys=result_dict.keys(),
            )
    # Add a return statement for cases where the depth of splits is neither 1 nor 2
    raise ValueError("The depth of the splits dictionary must be 1 or 2.")


if __name__ == "__main__":
    print("Hello from pointcloud.py. Nothing to see here.")
