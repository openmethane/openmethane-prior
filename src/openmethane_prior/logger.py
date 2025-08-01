#
# Copyright 2025 The Superpower Institute
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import os
import pathlib

def _parse_logger_env():
    """
    Parses environment variables and sets up logging based on their values.

    LOG_LEVEL - must be a valid logging level from the builtin logging package.
      Sets the log level of the base logger and all logs accessed via get_logger.

    LOG_FILE - a filename where the logger should attempt to log. If the
      provided filename already exists, it will attempt to move the existing
      file by prefixing the filename with `000`, `001`, etc.

    :return: (log_level, log_file_handler)
    """
    LOG_LEVEL = os.getenv("LOG_LEVEL", None)

    # Set a default log level based on the LOG_LEVEL environment var
    log_level = logging.INFO
    if LOG_LEVEL is not None:
        log_levels = logging.getLevelNamesMapping()
        if LOG_LEVEL in log_levels.keys():
            log_level = log_levels[LOG_LEVEL]
        else:
            valid_levels = ', '.join(log_levels.keys())
            logging.warning(
                f"LOG_LEVEL={LOG_LEVEL} is not a valid log level, must be one of: {valid_levels}"
            )

    # Log to a file if a filename is provided in the LOG_FILE environment var
    log_file = os.getenv("LOG_FILE", None)
    if log_file is not None:
        # if a file already exists at that path, move it
        if os.path.isfile(log_file):
            file_dir = os.path.dirname(log_file)
            file_name = os.path.basename(log_file)
            rotation = 0
            rotate_log_name = pathlib.Path(file_dir, f"{f'{rotation:03d}'}.{file_name}")
            while os.path.exists(rotate_log_name):
                rotation += 1
                rotate_log_name = pathlib.Path(file_dir, f"{f'{rotation:03d}'}.{file_name}")
            os.rename(log_file, rotate_log_name)

    return log_level, log_file

# configure logging automatically when this module is invoked
log_level, log_file = _parse_logger_env()
logging.basicConfig(level=log_level)

def get_logger(package_name: str) -> logging.Logger:
    logger = logging.getLogger(package_name)
    logger.setLevel(log_level)

    # add file handler so log output goes to the terminal and the file
    if log_file is not None:
        logger.addHandler(logging.FileHandler(log_file))

    return logger


