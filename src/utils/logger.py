import logging
import sys

def setup_logger(name, log_file=None, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler_console = logging.StreamHandler(sys.stdout)
    handler_console.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler_console)
    
    if log_file:
        handler_file = logging.FileHandler(log_file)
        handler_file.setFormatter(formatter)
        logger.addHandler(handler_file)
        
    return logger
