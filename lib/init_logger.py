import logging
import os
from datetime import datetime

def init_logger(log_name, verbose=True):
    logger = logging.getLogger(log_name)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y.%m.%d-%H:%M:%S")

    # Get today's date to create a folder named after the date
    today = datetime.today().strftime('%Y-%m-%d')  # Format like "2025-07-22"
    log_dir = os.path.join("log", today)  # Create a log folder with the current date

    os.makedirs(log_dir, exist_ok=True)  # Ensure the directory exists, create it if it doesn't

    # Create a unique log file name by appending a timestamp to the base name
    timestamp = datetime.now().strftime('%H-%M-%S')  # Example: "15-30-45"
    log_file_name = f"{log_name}_{timestamp}.log"  # Example: "test_15-30-45.log"
    log_path = os.path.join(log_dir, log_file_name)

    # Set log level
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Create file handler for logging to a file
    file_handler = logging.FileHandler(log_path, mode='w')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Create stream handler for logging to the console
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
