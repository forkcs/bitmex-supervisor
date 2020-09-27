import logging


def setup_api_logger(name, log_level=logging.DEBUG):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - CORE:      %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(handler)
    return logger


def setup_supervisor_logger(name, log_level=logging.INFO):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - SUPERVISOR:  %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(handler)
    return logger
