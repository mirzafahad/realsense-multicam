"""
This handles realsense camera frames in a separate process.
"""

import logging
import multiprocessing
import time
from multiprocessing.shared_memory import SharedMemory
from typing import Any

import numpy as np
import pyrealsense2 as rs
from numpydantic import NDArray

from multicam.data_contract import (
    CameraConfiguration,
    SharedMemoryNdArray,
    SharedMemoryFrameset,
)
from multicam.utils import remove_shm_from_resource_tracker


class CameraFrameProducer(multiprocessing.Process):
    """
    Read camera frames from a realsense camera.

    Once we read a frame, we save it in a shared memory and
    pass the name of the shared memory downstream for processing.

    Args:
        camera_config: Camera configuration.
        output_queue: Output queue where the producer will pass the frames.
    """

    def __init__(
        self, camera_config: CameraConfiguration, output_queue: multiprocessing.Queue
    ):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}_{camera_config.alias}")

        self.camera_config = camera_config
        self.output_queue = output_queue

        # Realsense camera pipeline.
        self.pipeline: Any = None

        # The following will disable resource tracking of shared memory for the child process.
        # Since the shared memory will be released in the main process.
        remove_shm_from_resource_tracker()

    def init_in_run(self) -> None:
        """
        This initialization happens inside the run(). By doing this, we are
        avoiding the pickling for pyrealsense2. pyrealsense2 is not pickable.
        """

        rs_config = rs.config()
        rs_config.enable_device(self.camera_config.serial_number)

        width, height = self.camera_config.frame_dimensions
        rs_config.enable_stream(
            rs.stream.color, width, height, rs.format.rgb8, self.camera_config.fps
        )
        rs_config.enable_stream(
            rs.stream.depth, width, height, rs.format.z16, self.camera_config.fps
        )

        self.pipeline = rs.pipeline()
        self.pipeline.start(rs_config)
        self.logger.info(f"Camera {self.camera_config.serial_number} pipeline started!")

        # Make sure that the camera is connected to a USB3 port.
        usb_type_descriptor = self._get_usb_type_descriptor()
        if not usb_type_descriptor.startswith("3"):
            raise SystemError(
                f"camera_{self.camera_config.alias}({self.camera_config.serial_number}) "
                "is not connected to USB3!"
            )

    def _get_usb_type_descriptor(self) -> str:
        usb_type = (
            self.pipeline.get_active_profile()
            .get_device()
            .get_info(rs.camera_info.usb_type_descriptor)
        )
        return str(usb_type)

    def run(self) -> None:
        """
        Continuously read frames from the realsense camera.
        """
        self.init_in_run()

        while True:
            try:
                frameset = self.pipeline.wait_for_frames(5000)  # 5 seconds.
                color_frame = np.asarray(frameset.get_color_frame().get_data())
                depth_frame = np.asarray(frameset.get_depth_frame().get_data())

                color_frame_shm = self._convert_np_array_to_shared_memory_array(
                    color_frame
                )
                depth_frame_shm = self._convert_np_array_to_shared_memory_array(
                    depth_frame
                )

                shm_frameset = SharedMemoryFrameset(
                    color_frame=color_frame_shm,
                    depth_frame=depth_frame_shm,
                    camera_config=self.camera_config,
                    timestamp=time.time(),
                )
                self.output_queue.put(shm_frameset)
            except Exception as e:
                self.logger.error(e)
                self.pipeline.stop()
                break

    @staticmethod
    def _convert_np_array_to_shared_memory_array(
        np_array: NDArray,
        sm_name: str | None = None,
    ) -> SharedMemoryNdArray:
        """
        Create a shared memory from a numpy array.

        Args:
            np_array: Numpy array to save in a shared memory.
            sm_name: Name for the shared memory. Default (None) will generate random name,
                which is preferable. Use a fixed name during unit-testing.

        Returns:
            SharedMemoryNdArray with np_array saved in the shared memory buffer.
        """
        # Note: If name is None, SharedMemory will assign a random name.
        shared_memory = SharedMemory(name=sm_name, create=True, size=np_array.nbytes)

        # Create a new numpy array that uses the shared memory.
        sm_np_array: NDArray = np.ndarray(
            shape=np_array.shape,
            dtype=np_array.dtype,
            buffer=shared_memory.buf,
        )

        # Copy the numpy array to the shared memory buffer.
        np.copyto(dst=sm_np_array, src=np_array)

        # Closing the memory because this class doesn't use the data here.
        # It will pass to a different process for processing, and we will open it there.
        shared_memory.close()

        # We can read the data as long as we know the name of the memory.
        return SharedMemoryNdArray(
            memory_name=shared_memory.name,
            np_array_dtype=np_array.dtype,
            np_array_shape=np_array.shape,
        )
