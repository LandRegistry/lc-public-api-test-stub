import os


class Config(object):
    DEBUG = False
    APPLICATION_NAME = "lc-public-api-test"


class DevelopmentConfig(Config):
    DEBUG = True


class PreviewConfig(Config):
    pass
