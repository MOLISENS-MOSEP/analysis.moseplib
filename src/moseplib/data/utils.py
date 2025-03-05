from bisect import bisect_left, bisect_right
import pandas as pd
from pointcloudset import PointCloud, Dataset
from typing import NamedTuple, Union


class Limits(NamedTuple):
    x_min: Union[float, None] = None
    x_max: Union[float, None] = None
    y_min: Union[float, None] = None
    y_max: Union[float, None] = None
    z_min: Union[float, None] = None
    z_max: Union[float, None] = None
    r_min: Union[float, None] = None
    r_max: Union[float, None] = None

    def apply_limits(self, pc: PointCloud) -> PointCloud:
        """
        Applies limits to a PointCloud object along the x, y, and z dimensions.

        Args:
            pc (PointCloud): The PointCloud object to apply the limits to.

        Returns:
            PointCloud: A new PointCloud object with the limits applied.
        """

        x_min = float("-inf") if self.x_min is None else self.x_min
        x_max = float("inf") if self.x_max is None else self.x_max
        y_min = float("-inf") if self.y_min is None else self.y_min
        y_max = float("inf") if self.y_max is None else self.y_max
        z_min = float("-inf") if self.z_min is None else self.z_min
        z_max = float("inf") if self.z_max is None else self.z_max
        r_min = float("-inf") if self.r_min is None else (self.r_min * 1e3)  # convert m to mm
        r_max = float("inf") if self.r_max is None else (self.r_max * 1e3)

        return (
            pc.limit(dim="x", minvalue=x_min, maxvalue=x_max)
            .limit(dim="y", minvalue=y_min, maxvalue=y_max)
            .limit(dim="z", minvalue=z_min, maxvalue=z_max)
            .limit(dim="range", minvalue=r_min, maxvalue=r_max)
        )

    def replace(self, **kwargs):
        """
        Returns a new Limits object replacing specified fields with new values

        Args:
            **kwargs: fields to replace with new values.

        Returns:
            Limits: A new Limits object with the replaced fields.
        """
        return self._replace(**kwargs)

    def get_vertices_from_limits(self, format: str = "xyz"):
        """Calculates the coordinates of the 8 vertices of a cube given the minimum and maximum values for each
        dimension.

        Possible formats for the output: xyz_lists and vertices_list.
        - xyz_lists format returns the x, y, and z coordinates of each vertex as separate lists. This format is useful when
        you need to work with the x, y, and z coordinates separately, for example, when plotting the vertices using a
        library like Matplotlib or Plotly.
        - vertices_list format returns a list of tuples, where each tuple represents the x, y, and z coordinates of a
        vertex. This format is useful when you need to work with the vertices as a whole, for example, when calculating the
        distance between two vertices or when performing operations on the vertices as a group

        Args:
            limits (object): An object that has the following attributes: x_min, x_max, y_min, y_max, z_min, z_max.
            format (str, optional): The format of the output. Can be 'xyz' or 'vertices'. Defaults to 'xyz'.

        Raises:
            ValueError: If the format is not supported.

        Returns:
            tuple or list: The coordinates of the 8 vertices of the cube.
        """

        vertices = [
            (self.x_min, self.y_min, self.z_min),
            (self.x_min, self.y_max, self.z_min),
            (self.x_max, self.y_max, self.z_min),
            (self.x_max, self.y_min, self.z_min),
            (self.x_min, self.y_min, self.z_max),
            (self.x_min, self.y_max, self.z_max),
            (self.x_max, self.y_max, self.z_max),
            (self.x_max, self.y_min, self.z_max),
        ]

        if format == "xyz":
            return zip(*vertices)
        elif format == "vertices":
            return vertices
        else:
            raise ValueError("Format not supported.")


def take_closest(sorted_list, value, get_index=False, position="left"):
    """Returns the closest value to `value` in a sorted list.

    Also works for datetime objects which means it can be used to choose a Pointcloud from a Dataset.
    If two numbers are equally close, return the smaller number (position="left") or the bigger number
    (position="right").

    Args:
        sorted_list (List[Union[int, float]]): A sorted list of integers or floats.
        value (Union[int, float]): The value to find the closest match for.
        get_index (bool, optional): If True, return the index of the closest value instead of the value itself.
            Defaults to False.
        position (str, optional): The position of the closest value to return. Can be "left" or "right".
            Defaults to "left".

    Returns:
        Union[int, float, int]: The closest value to `value` in `sorted_list`, or its index if `get_index` is True.

    Raises:
        ValueError: If `sorted_list` is empty.

    Examples:
        >>> take_closest([1, 2, 3, 4, 5], 3.6)
        4
        >>> take_closest([1, 2, 3, 4, 5], 3.6, get_index=True)
        3
    """
    if position == "left":
        pos = bisect_left(sorted_list, value)
    elif position == "right":
        pos = bisect_right(sorted_list, value)

    if get_index:
        return pos
    if pos == 0:
        return sorted_list[0]
    if pos == len(sorted_list):
        return sorted_list[-1]
    before = sorted_list[pos - 1]
    after = sorted_list[pos]
    if after - value < value - before:
        return after
    else:
        return before


def take_closest_unsorted(unsorted_list, value):
    return min(unsorted_list, key=lambda x: abs(x - value))


def get_pointcloud_from_timestamp(ds: Dataset, timestamp: str, position: str = "left") -> PointCloud:
    """Get the PointCloud closest to a given timestamp from a Dataset.

    Args:
        ds (Dataset): The Dataset object to search for the PointCloud.
        timestamp (str): The timestamp to search for in a format understood by pandas.to_datetime.

    Returns:
        PointCloud: The PointCloud closest to the given timestamp.
    """
    closest = take_closest(ds.timestamps, pd.to_datetime(timestamp), position=position)
    return ds[ds._get_pointcloud_number_from_time(closest)]


def normalize_df(df: pd.DataFrame, kind: str = "standard", fillna: bool = False) -> pd.DataFrame:
    """
    Normalizes a DataFrame using either standard or min-max normalization.

    This function applies either standard normalization (z-score normalization) or min-max normalization to a DataFrame.
    The type of normalization is determined by the `kind` parameter.

    Note: To avoid getting NaN values for timeseries with no variation, use fillna=True to fill NaN values with 0 after
    normalization.

    Args:
        df (pd.DataFrame): The input DataFrame to normalize.
        kind (str, optional): The type of normalization to apply. If "standard", applies standard normalization. If
            "minmax", applies min-max normalization. Defaults to "standard".
        fillna (bool, optional): If True, fill NaN values with 0 after normalization. Defaults to False.

    Returns:
        pd.DataFrame: The normalized DataFrame.

    Raises:
        ValueError: If the `kind` parameter is not "standard" or "minmax".
    """
    df = df.copy()
    if kind == "standard":
        result = (df - df.mean()) / df.std()
    elif kind == "minmax":
        result = (df - df.min()) / (df.max() - df.min())
    else:
        raise ValueError(f"Normalization kind {kind} not supported. Use 'standard' or 'minmax'.")

    if fillna:
        return result.fillna(0)
    return result


def flatten_multiindex(df: pd.DataFrame, sep: str = ".", levels: int = 1) -> Union[pd.Index, pd.MultiIndex]:
    """
    Modifies a DataFrame with a MultiIndex column or index IN PLACE, flattening it into a single-level column DataFrame
    or index DataFrame, depending on the value of the `levels` parameter. The DataFrame will have columns or index
    with names that are a concatenation of the levels of the MultiIndex, separated by the `sep` parameter. Returns the
    original MultiIndex columns or index for later use.

    Args:
        df (pd.DataFrame): The input DataFrame with a MultiIndex column or index to flatten in place.
        sep (str, optional): The separator to use when concatenating the levels of the MultiIndex. Defaults to ".".
        levels (int, optional): The level to flatten. If 0, flattens the index. If 1, flattens the columns.
            Defaults to 1.

    Returns:
        Union[pd.Index, pd.MultiIndex]: The original MultiIndex columns or index before flattening.
    """
    if levels == 0:
        if not isinstance(df.index, pd.MultiIndex):
            raise ValueError("DataFrame does not have a MultiIndex index.")
        original_index = df.index.copy()
        df.index = [sep.join(map(str, idx)).strip() for idx in df.index.values]
        return original_index
    elif levels == 1:
        if not isinstance(df.columns, pd.MultiIndex):
            raise ValueError("DataFrame does not have a MultiIndex column.")
        original_columns = df.columns.copy()
        df.columns = [sep.join(map(str, col)).strip() for col in df.columns.values]
        return original_columns
    else:
        raise ValueError("Levels parameter must be 0 or 1.")


if __name__ == "__main__":
    limits = Limits(x_min=0, x_max=10, y_min=0, y_max=10, z_min=0, z_max=10)
    print(limits.get_vertices_from_limits())
    print(limits.get_vertices_from_limits(format="vertices"))
