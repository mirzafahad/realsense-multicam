import multiprocessing
import logging
from multicam.camera import CameraFrameProducer
from multicam.data import CameraConfiguration
from multicam.viewer import CameraFrameViewer

# The cameras are placed in a circle. The position of the camera
# are used as alias for the camera to easily identify in real world.
cameras = {
    "TWO_O_CLOCK": "010203",
    "FOUR_O_CLOCK": "040506",
    "SIX_O_CLOCK": "070809",
    "EIGHT_O_CLOCK": "101112",
    "TEN_O_CLOCK": "131415",
    "TWELVE_O_CLOCK": "161718",
}


def main() -> None:
    logger = logging.getLogger(f"{__name__}")

    camera_processes = []
    output_queue = multiprocessing.Queue()  # type: multiprocessing.Queue

    for camera_name, serial_number in cameras.items():
        # Using default fps and resolutions.
        camera_config = CameraConfiguration(
            alias=camera_name,
            serial_number=serial_number,
        )
        camera_process = CameraFrameProducer(camera_config, output_queue)
        camera_process.start()
        camera_processes.append(camera_process)

    logger.info("All camera processes started!")
    frame_viewer = CameraFrameViewer(output_queue)

    while True:
        frame_viewer.show_frames()
