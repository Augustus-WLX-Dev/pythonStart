# demo for line 1-84

import logging
import os
import sys

class SimpleLogger:
    """ Simple logger class """

    def __init__(self,name:str):
        self.name = name

        os.makedirs("demo_logs", exist_ok = True)
        self.log_filename = f"demo_logs/{name}_log.txt"
        self.original_stdout = sys.stdout
        self.initialize_logger()

    """ setup logger """
    def initialize_logger(self):
        self.logger = logging.getLogger(f"demo_logger_{self.name}")
        self.logger.setLevel(logging.INFO)

        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create file handler
        file_handler = logging.FileHandler(self.log_filename)
        file_handler.setLevel(logging.INFO)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Create different formatters for file and console
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')

        # Set formatters
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handler to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Prevent propagation to root logger to avoid duplicate messages
        self.logger.propagate = False

    def test_logging(self):
        self.logger.info("测试开始")
        self.logger.warning("这是一个警告")
        self.logger.error("这是一个错误")

if __name__ == "__main__":
    # creating SimpleLogger("BTC") object
    simple_logger = SimpleLogger("BTC")
    simple_logger.test_logging()

