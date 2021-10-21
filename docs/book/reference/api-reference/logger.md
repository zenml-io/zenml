Module zenml.logger
===================

Functions
---------

    
`get_console_handler() ‑> Any`
:   Get console handler for logging.

    
`get_file_handler() ‑> Any`
:   Return a file handler for logging.

    
`get_logger(logger_name) ‑> Any`
:   Main function to get logger name,.
    
    Args:
      logger_name: Name of logger to initialize.
    
    Returns:
        A logger object.

    
`get_logging_level() ‑> zenml.enums.LoggingLevels`
:   Get logging level from the env variable.

    
`init_logging()`
:   Initialize logging with default levels.

    
`set_root_verbosity()`
:   Set the root verbosity.