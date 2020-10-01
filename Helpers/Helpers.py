import json
from SlaveContainer import SlaveContainer
import logging
import logging.config
import sys
import os

import numpy as np
# import pandas as pd
import sqlite3 as sql


############################################
## -- Helper Functions
############################################

ROOT_DIR = os.path.abspath(os.curdir)


def create_logger():
    # create logger
    logger = logging.getLogger('cct')

    # check if logger already been created
    if logger.hasHandlers():
        return logger

    # Create handlers
    c_handler = logging.StreamHandler(stream=sys.stdout)
    f_handler = logging.FileHandler(f'{ROOT_DIR}/logs/cct.log', mode='w')
    c_handler.setLevel(logging.DEBUG)
    f_handler.setLevel(logging.DEBUG)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)
    logger.setLevel(logging.DEBUG)

    return logger


def server_begin():
    ############################################
    ## -- Server Preparation
    ############################################

    logger = create_logger()
    logger.info('The Crypto-Copy-Trader starts launch')

    with open(f'{ROOT_DIR}/config_files/config.json', 'r') as config_f:
        config = json.load(config_f)

    logger.info('Reading configuration file...')
    logger.info(f'{len(config["slaves"])} Slave accounts detected')

    file = open(f'{ROOT_DIR}/config_files/symbols.csv', "r")
    symbols = file.readlines()

    slave_container = SlaveContainer(config, symbols)

    return slave_container



