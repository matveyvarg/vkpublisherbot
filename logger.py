import logging


class LevelFilterBelow(logging.Filter):
    def __init__(self, level):
        self.__level = level

    def filter(self, record):
        return record.levelno <= self.__level


class LevelFilterAbove(logging.Filter):
    def __init__(self, level):
        self.__level = level

    def filter(self, record):
        return record.levelno >= self.__level


# LOGGING
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

errorHandler = logging.FileHandler("errors.log")
errorHandler.setLevel(logging.WARNING)
errorHandler.addFilter(LevelFilterAbove(logging.WARNING))
errorHandler.setFormatter(formatter)

handler = logging.FileHandler("logs.log")
handler.setLevel(logging.INFO)
handler.addFilter(LevelFilterBelow(logging.INFO))
handler.setFormatter(formatter)


def get_logger(name=__name__):
    logger = logging.getLogger(name)

    logger.addHandler(errorHandler)
    logger.addHandler(handler)

    return logger
