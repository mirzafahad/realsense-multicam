import logging
import traceback

from multicam.app import main

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"EXCEPTION: {type(e).__name__}-{e}")
        print(f"{traceback.format_exc()}")
