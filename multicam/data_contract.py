"""
The data structure the application uses.
"""
import time
from dataclasses import dataclass, field
from enum import IntEnum
from multiprocessing.shared_memory import SharedMemory

import numpy as np
from numpy.typing import DTypeLike
from numpydantic import NDArray
from pydantic import BaseModel as PyBaseModel
from pydantic import Field, ConfigDict


class BaseModel(PyBaseModel):
    # Allowing base models to have arbitrary (custom) types
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RotationAngle(IntEnum):
    """
    Describes the clockwise rotation angle used to rotate an
    RgbdFrameset.

    The values of the IntEnum aren't arbitrary.
    It's important that they have exactly these values so
    that we can always know how many rotations it takes
    to get back to the original orientation via
    (4 - current_rotation_angle) mod 4.
    """

    ANGLE_0 = 0
    ANGLE_90 = 1
    ANGLE_180 = 2
    ANGLE_270 = 3

    def to_degrees(self) -> int:
        """
        Get the current rotation angle in integer degrees.

        Example:RotationAngle.ANGLE_90.to_degrees()
        """
        return self.value * 90

    @staticmethod
    def from_degrees(angle: int) -> "RotationAngle":
        """
        Builds a `RotationAngle` from integer degrees.

        Args:
            angle: one of `[0, 90, 180, 270]`.

        Raises:
            ValueError: if not in `[0, 90, 180, 270]`.
        """
        if angle not in [0, 90, 180, 270]:
            raise ValueError("Angle must be one of 0, 90, 180, 270")

        return RotationAngle(angle // 90)


class CameraConfiguration(BaseModel):
    """
    Camera information from RGBD and calibration parameters.
    """

    # User-provided name for clarity.
    alias: str = ""

    # USB connection type (e.g., 3.2 or 2.1).
    # Useful for verifying camera is connected to the right USB port.
    usb_type_descriptor: str = ""

    # Camera firmware version. Populated by pyrealsense2.
    firmware_version: str = ""

    # Camera serial number.
    serial_number: str

    # (width, height) for both color and depth.
    frame_dimensions: tuple[int, int] = Field(default=(424, 240))

    # Frames per second.
    fps: int = Field(default=5)

    # Rotation angle of the final frame.
    rotation_angle: RotationAngle = Field(default=RotationAngle.ANGLE_0)

    def get_int_rotation_angle(self) -> int:
        """
        Get the integer equivalent of the enum angle.
        """
        match self.rotation_angle:
            case RotationAngle.ANGLE_0:
                return 0
            case RotationAngle.ANGLE_90:
                return 90
            case RotationAngle.ANGLE_180:
                return 180
            case RotationAngle.ANGLE_270:
                return 270
            case _:
                raise AttributeError(f"Invalid angle: {self.rotation_angle}")


@dataclass
class SharedMemoryNdArray:
    """
    Shared memory info that represents a numpy array.
    """

    memory_name: str
    np_array_dtype: DTypeLike
    np_array_shape: tuple[int, ...]

    def get_np_array(self) -> NDArray:
        """
        Extract the numpy array from the shared memory array.

        Returns:
            numpy_array: Copy of the numpy array from the shared memory.
        """
        shared_memory = SharedMemory(name=self.memory_name)

        # Create a new numpy array that uses the shared memory.
        sm_numpy_array: NDArray = np.ndarray(
            shape=self.np_array_shape,
            dtype=self.np_array_dtype,
            buffer=shared_memory.buf,
        )
        numpy_array = sm_numpy_array.copy()
        shared_memory.close()
        return numpy_array

    def unlink_memory(self) -> None:
        """
        Unlinks the shared memory, which will destroy the underlying
        shared memory block, so that it can be reused.
        """
        shared_memory = SharedMemory(name=self.memory_name)
        shared_memory.close()
        shared_memory.unlink()


@dataclass
class SharedMemoryFrameset:
    """
    A camera-frame in a shared memory, along with camera configurations.
    """

    # We are passing camera frames through shared memory.
    color_frame: SharedMemoryNdArray
    depth_frame: SharedMemoryNdArray
    camera_config: CameraConfiguration
    timestamp: float = field(default_factory=time.time)

    def unlink_all_memory(self) -> None:
        """
        Unlink the shared memories. This will delete the reference of the memory.
        """
        self.color_frame.unlink_memory()
        self.depth_frame.unlink_memory()

    def get_depth(self) -> NDArray:
        """
        Get depth frame from the shared memory.
        Note: We will get a copy of the data from the shared memory.
        """
        return self.depth_frame.get_np_array()

    def get_color(self) -> NDArray:
        """
        Get color frame from the shared memory.
        Note: We will get a copy of the data from the shared memory.
        """
        return self.color_frame.get_np_array()

    @property
    def camera_alias(self) -> str:
        """
        The custom name of the camera.
        """
        return self.camera_config.alias
