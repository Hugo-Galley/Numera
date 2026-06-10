# Logging in Suivi Budget

This document describes how logging is implemented in the Suivi Budget backend and how to use it.

## Overview

The application uses the standard Python `logging` module, configured in `app/core/logging.py`. 
Logs are sent to `stdout`, which is standard for Dockerized applications.

### Log Levels
- **DEV**: `DEBUG` level is active.
- **PROD/Others**: `INFO` level is active.

## How to use in code

To add logging to a new module, follow these steps:

1. Import `get_logger` from `app.core.logging`.
2. Initialize the logger at the top of your file.
3. Use the logger in your functions.

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

def my_function():
    logger.info("Doing something...")
    try:
        # business logic
        pass
    except Exception as e:
        logger.error(f"Something went wrong: {e}", exc_info=True)
        raise
```

## Automatic Logging

### Request Logging
A middleware in `app/main.py` automatically logs every incoming HTTP request (except successful `/health` checks) with its method, path, status code, and duration.

Example:
`2026-06-03 10:00:00,000 - app.main - INFO - method=GET path=/accounts status=200 duration=15.42ms`

### Error Logging
The same middleware catches any unhandled exceptions, logs the error message, and provides the full traceback in the logs before re-raising the exception.

Example:
`2026-06-03 10:00:00,000 - app.main - ERROR - method=POST path=/import/commit error=Invalid amount <= 0 duration=42.10ms`
(followed by the traceback)

## Configuration

Logging is initialized in `app/main.py` via `setup_logging()`. 

You can adjust specific logger levels in `app/core/logging.py` if some libraries are too verbose (e.g., `uvicorn.access` or `sqlalchemy.engine`).
