import multiprocessing
import sys
import time

import cv2
import numpy as np
from numpydantic import NDArray
from pydantic import BaseModel, Field

from multicam.data import SharedMemoryFrameset


class FpsStats(BaseModel):
    """
    To keep track of camera FPS.
    """

    count: int = 0
    start_time: float = Field(default_factory=time.time)
    fps: float = 0.0
    last_frame_time: float = 0.0


class CameraFrame(BaseModel):
    """
    Each frame consists of the image and fps stats.
    """

    image: NDArray
    fps_stats: FpsStats = Field(default_factory=FpsStats)


class CameraFrameViewer:
    """
    View camera frames real-time.
    Args:
        frame_q: The queue cameras use to send frames.
    """

    def __init__(self, frame_q: multiprocessing.Queue):
        self.frame_q = frame_q

        # Keep track of camera alias and associated camera-frame.
        self.camera_frames: dict[str, CameraFrame] = {}

    def show_frames(self) -> None:
        """
        Show the frames in a grid.
        """
        while True:
            frameset = self.frame_q.get()  # type: SharedMemoryFrameset
            self._update_frame_on_display_grid(frameset)
            self.show_display_grid()

            # Once we display the frame, unlink it, so that we can free the shared memory.
            frameset.unlink_all_memory()

    def _update_frame_on_display_grid(self, frameset: SharedMemoryFrameset) -> None:
        """
        The frames come asynchronously. We only update one frame on the display grid,
        the one we received and keep the rest images same from the last time we received.
        """
        camera_frame = self.camera_frames.get(frameset.camera_alias, None)
        if camera_frame is None:
            # This is the first time we are receiving the frame from this camera.
            camera_frame = CameraFrame(image=frameset.get_color())
            self.camera_frames[frameset.camera_alias] = camera_frame

        camera_frame.fps_stats = self._update_fps_stats(camera_frame.fps_stats)

        camera_frame.image = self._overlay_info_on_image(
            image_rgb=frameset.get_color(),
            label=frameset.camera_alias,
            fps=camera_frame.fps_stats.fps,
        )

    def show_display_grid(self) -> None:
        """
        Show up to six camera frames in a 2x3 grid.
        """
        images = []
        for _, camera_frame in self.camera_frames.items():
            images.append(camera_frame.image)

        # The grid is 2x3.
        if 0 < len(images) < 6:
            # If there aren't all 6 images, use black image.
            black_image = np.zeros(images[0].shape, dtype=np.uint8)
            for _ in range(6 - len(images)):
                images.append(black_image)

        top_row = np.hstack(images[:3])
        bottom_row = np.hstack(images[3:])
        grid_image = np.vstack([top_row, bottom_row])

        # Show display
        cv2.imshow("Real-time view of Cameras", grid_image)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()

    @staticmethod
    def _update_fps_stats(fps_stats: FpsStats) -> FpsStats:
        """
        Keep track of FPS for each camera.

        Increment frame counter by one and calculate fps if more than one second is passed.
        """
        current_time = time.time()
        fps_stats.count += 1
        fps_stats.last_frame_time = current_time

        # Update FPS every second
        elapsed = current_time - fps_stats.start_time
        if elapsed >= 1.0:
            fps_stats.fps = fps_stats.count / elapsed
            fps_stats.count = 0
            fps_stats.start_time = current_time

        return fps_stats

    @staticmethod
    def _overlay_info_on_image(
        image_rgb: NDArray, label: str, fps: float, timeout: bool = False
    ) -> NDArray:
        """
        Add label, border, "No Signal" and fps on the image.

        Args:
            image_rgb: The RGB image.
            label: Label for the image, usually the camera name or position.
            fps: The frame rate info to place on the image.
            timeout: If the image is timed out. Then we will place a red border instead of green.

        Returns:
             Updated image with border, fps and optional timeout info.
        """
        if timeout:
            image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

            border_color = (0, 0, 255)  # Red border for timeout
            label = f"{label}: NO SIGNAL"
        else:
            image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            border_color = (0, 255, 0)  # Green border

        image_with_border = cv2.copyMakeBorder(
            image, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=border_color
        )

        # Place label on the image.
        cv2.putText(
            image_with_border,
            label,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Place the fps on the image if available.
        if not timeout:
            cv2.putText(
                image_with_border,
                f"FPS: {fps:.1f}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

        return image_with_border
