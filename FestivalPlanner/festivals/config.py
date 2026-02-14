import os

import yaml


COMMON_CONFIG_PATH = os.path.expanduser('~/Projects/FilmFestivalPlanner/Configs/common.yml')


class Config:
    config = None
    config_path = COMMON_CONFIG_PATH

    def __init__(self):
        with open(self.config_path, 'r') as stream:
            self.config = yaml.safe_load(stream)
