import importlib.resources
from pathlib import Path


PACKAGE_NAME = "moseplib"

PATH_TO_LUFFT_MSGS = importlib.resources.files(PACKAGE_NAME) / Path("config/custom_ros_msgs/lufft_wsx_interfaces/msg")

PC_TOPICS = [
    "/sensing/lidar/points",
    "/sensing/lidar/points2",
    "/sensing/radar/points",
]
FIELDS = ["x", "y", "z", "intensity", "t", "reflectivity", "ring", "ambient", "range", "original_id"]
