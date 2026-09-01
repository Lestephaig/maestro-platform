import json
import logging
from datetime import datetime, timezone


class SafeJsonFormatter(logging.Formatter):
    """JSON formatter that emits only explicitly approved fields."""

    SAFE_FIELDS = ('event', 'error_type', 'has_deep_link', 'button_count')

    def format(self, record):
        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'event': getattr(record, 'event', 'unstructured_log'),
        }
        for field in self.SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    # HTTP request URLs contain the bot token. Even if a dependency raises its
    # verbosity, SafeJsonFormatter never includes the original log message.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
