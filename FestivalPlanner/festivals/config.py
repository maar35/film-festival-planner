import os

import yaml


class Config:
    config = None
    config_path = os.path.expanduser('~/Projects/FilmFestivalPlanner/Configs/common.yml')

    def __init__(self):
        with open(self.config_path, 'r') as stream:
            self.config = yaml.safe_load(stream)
