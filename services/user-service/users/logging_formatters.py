"""
Custom JSON logging formatter
"""

import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """Format logs as JSON"""

    def format(self, record):
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "context"):
            # Ensure context is JSON serializable (e.g., DRF view instances cause errors)
            try:
                json.dumps(record.context)
                log_data["context"] = record.context
            except TypeError:
                # Fallback to string representation
                log_data["context"] = str(record.context)

        return json.dumps(log_data)
