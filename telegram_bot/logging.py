import json
import logging
from datetime import datetime, timezone


class TelegramJsonFormatter(logging.Formatter):
    """Small JSON formatter with an explicit allow-list of safe fields."""

    SAFE_FIELDS = ('event', 'error_type', 'has_deep_link', 'button_count')

    def format(self, record):
        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'event': getattr(record, 'event', record.getMessage()),
        }
        for field in self.SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False)
