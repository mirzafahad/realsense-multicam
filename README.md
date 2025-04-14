# Multi Realsense Camera Frame Capture on Jetson Nano

Stream and process frames from **up to six Intel Realsense cameras** in parallel on an 
**NVIDIA Jetson Nano** using **Python multiprocessing** and **shared memory**. 
This project is optimized for edge performance and provides a robust architecture for 
high-bandwidth vision tasks.

It works effectively with 2 to 6 cameras (I have not tested beyond 6 due to USB port limitations).
With 2 cameras, I was able to achieve 30 fps. With 6 cameras, the frame rate dropped to around 5 fps. 
Your results may vary depending on your setup.

## Hardware Used
- NVIDIA Jetson Nano (4GB)
- Intel Realsense D405 (x6)

## Key Concepts

- **Multiprocessing**: Run each camera in a separate process for true parallelism.
- **Shared Memory**: Transfer large amount of camera frames without memory duplication.
- **pyrealsense2 Integration**: Carefully manage unpicklable objects.
- **Resource Tracker Patch**: Fix Python's shared memory leak issue across processes.

## Architecture
- Each camera-frame-producer process captures frames and writes to shared memory.
- Then pass the shared-memory-metadata to a shared queue.
- A central consumer process reads the frames from the queue for post-processing 
(in this example I will simply display the frames).
- Once a frame is processed, release/unlink the corresponding shared memory.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/mirzafahad/realsense-multicam.git
cd realsense-multicam
```
### 2. Install Python
You will at least need Python 3.11.8. Check the [download](https://www.python.org/downloads/) section for all the releases.

### 3. Install Poetry
The project uses [Poetry](https://python-poetry.org/docs/) for dependency management. 
At the time of writing I am using version 1.8.5.

```bash
pipx install poetry==1.8.5
poetry --version
```

### 4. Install project
If you are already in the project directory then:
```bash
poetry install
```

### 5. Run the Application
Make sure all Realsense cameras are connected and detected before starting.
Update the variable `CAMERAS` with the camera serial numbers in `config.py`. 

```bash
poetry shell
python run -m multicam
```

## References
- [Python Multiprocessing](https://docs.python.org/3/library/multiprocessing.html)
- [Python Shared Memory](https://docs.python.org/3/library/multiprocessing.shared_memory.html)
- [Intel RealSense SDK](https://github.com/IntelRealSense/librealsense)

---
# Author
Find me on [LinkedIn](https://www.linkedin.com/in/fahadmirza1/).
If this helped, feel free to ⭐ the repo!
