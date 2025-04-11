import sys

from multicam.data import SharedMemoryFrameset
import multiprocessing
import cv2
import numpy as np
import time
from pydantic import BaseModel, Field
from numpydantic import NDArray


class FpsStats(BaseModel):
    count: int = 0
    start_time: float = Field(default_factory=time.time)
    fps: float = 0.0
    last_frame_time: float = 0.0


class CameraFrame(BaseModel):
    image: NDArray
    fps_stats: FpsStats = Field(default_factory=FpsStats)


class CameraFrameViewer:
    """
    View camera frames real-time.
    """

    def __init__(self, frame_q: multiprocessing.Queue):
        """
        Args:
            frame_q: The queue cameras use to send frames.
        """
        self.frame_q = frame_q
        self.camera_frames = {}

    def show_frames(self):
        while True:
            frameset = self.frame_q.get()  # type: SharedMemoryFrameset
            self.update_display_grid(frameset)
            self.show_display_grid()
            frameset.unlink_all_frame_memory()

    def update_display_grid(self, frameset: SharedMemoryFrameset):
        camera_frame = self.camera_frames.get(frameset.camera_alias, None)
        if camera_frame is None:
            camera_frame = CameraFrame(image=frameset.get_color())
            self.camera_frames[frameset.camera_alias] = camera_frame
        else:
            camera_frame.image = frameset.get_color()

        camera_frame.fps_stats = self.update_fps_stats(camera_frame.fps_stats)

        camera_frame.image = self._update_image_with_stat(
            image_rgb=camera_frame.image,
            label=frameset.camera_alias,
            fps=camera_frame.fps_stats.fps,
        )

    def show_display_grid(self):
        images = []
        for _, camera_frame in self.camera_frames.items():
            images.append(camera_frame.image)

        if 0 < len(images) < 6:
            black_image = np.zeros(images[0].shape, dtype=np.uint8)
            for _ in range(6 - len(images)):
                images.append(black_image)
        top_row = np.hstack(images[:3])
        bottom_row = np.hstack(images[3:])
        grid_image = np.vstack([top_row, bottom_row])

        # Show display
        cv2.imshow("Per-Cam FPS", grid_image)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            sys.exit()

    @staticmethod
    def update_fps_stats(fps_stats: FpsStats) -> FpsStats:
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
    def _update_image_with_stat(
        image_rgb: NDArray, label: str, fps=None, timeout=False
    ) -> NDArray:
        """
        Add label, border, "No Signal" and fps on the image.

        Args:
            image_rgb: The RGB image.
            label: Label for the image, usually the camera name or posiiton.
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

        # Place label/camera-name on the image.
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
        if not timeout and fps is not None:
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

    # @staticmethod
    # def simulate_image_input():
    #     # Simulated camera input
    #     import random
    #     while True:
    #         cam_id = random.randint(0, project_config.NUM_CAMERAS - 1)
    #         img = np.random.randint(0, 256, (IMAGE_HEIGHT, IMAGE_WIDTH, 3), dtype=np.uint8)
    #         image_queue.put((cam_id, img))
    #         time.sleep(0.05 + 0.2 * random.random())  # Random timing
