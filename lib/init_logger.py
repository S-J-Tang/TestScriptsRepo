import logging
import os

def init_logger(log_name, verbose=True):
    logger = logging.getLogger(log_name)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y.%m.%d-%H:%M:%S")

    # Set log directory to a "log" folder
    log_dir = "log/"
    os.makedirs(log_dir, exist_ok=True)  # Ensure the directory exists, create it if it doesn't

    # Set log file path
    log_path = os.path.join(log_dir, log_name)

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
