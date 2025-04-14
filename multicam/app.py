import multiprocessing as mp
import logging
from multicam.config import CAMERAS
from multicam.camera import CameraFrameProducer
from multicam.data import CameraConfiguration, SharedMemoryFrameset
from multicam.viewer import CameraFrameViewer


def main() -> None:
    logger = logging.getLogger(f"{__name__}")

    camera_processes = []
    # All cameras will push there frames to this queue.
    output_queue = mp.Queue()  # type: mp.Queue

    # Start all camera processes using default configurations.
    for camera_name, serial_number in CAMERAS.items():
        # Using default fps and resolutions.
        camera_config = CameraConfiguration(
            alias=camera_name,
            serial_number=serial_number,
        )
        camera_process = CameraFrameProducer(camera_config, output_queue)
        camera_process.start()
        camera_processes.append(camera_process)

    logger.info("All camera processes started!")
    # Read frames from the queue and display.
    frame_viewer = CameraFrameViewer(output_queue)

    try:
        while True:
            frame_viewer.show_frames()
    except Exception as e:
        logger.warning(e)
    finally:
        # Shutdown the processes.
        for camera_process in camera_processes:
            camera_process.terminate()
            camera_process.join()
        logger.info("All camera processes terminated!")

        # Check for leftover shared-memory data and unlink them.
        if not output_queue.empty():
            logger.warning(f"Queue has shared-memory-frames: {output_queue.qsize()}")
            while not output_queue.empty():
                frameset = output_queue.get()  # type: SharedMemoryFrameset
                frameset.unlink_all_memory()
            logger.info("All shared memories are released.")
