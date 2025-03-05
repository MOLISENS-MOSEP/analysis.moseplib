import pandas as pd

from pointcloudset import PointCloud


def n_points(frame: PointCloud) -> pd.Series:
    return pd.Series([frame.data.N.sum()], index=[frame.timestamp])


def mean_intensity(frame: PointCloud) -> pd.Series:
    return pd.Series([frame.data.intensity.mean()], index=[frame.timestamp])


def sum_intensity(frame: PointCloud) -> pd.Series:
    return pd.Series([frame.data.intensity.sum()], index=[frame.timestamp])
