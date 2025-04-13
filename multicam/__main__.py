import logging
import traceback

from multicam.app import main

if __name__ == "__main__":
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Direct all logs to the console
    )
    logger = logging.getLogger(__name__)
    try:
        main()
    except Exception as e:
        # Catch all.
        logger.critical(f"EXCEPTION: {type(e).__name__}-{e}")
        logger.debug(f"{traceback.format_exc()}")
