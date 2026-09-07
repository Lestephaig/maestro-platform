import asyncio
import hashlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SUCCESS_RETENTION_SECONDS = 7 * 24 * 60 * 60
PROCESSING_LEASE_SECONDS = 5 * 60


@dataclass(frozen=True)
class ClaimResult:
    state: str
    telegram_message_id: int | None = None


class IdempotencyStore:
    """SQLite-backed successful-delivery registry without recipient data."""

    def __init__(self, path):
        self.path = Path(path)
        self._lock = asyncio.Lock()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=FULL')
        return connection

    async def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS telegram_deliveries (
                        key_hash TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        telegram_message_id INTEGER,
                        processed_at REAL NOT NULL
                    )
                    '''
                )
                self._cleanup(connection, time.time())
                connection.commit()
            finally:
                connection.close()

    @staticmethod
    def _hash_key(key):
        return hashlib.sha256(key.encode('utf-8')).hexdigest()

    @staticmethod
    def _cleanup(connection, now):
        connection.execute(
            '''
            DELETE FROM telegram_deliveries
            WHERE (status = 'succeeded' AND processed_at < ?)
               OR (status = 'processing' AND processed_at < ?)
            ''',
            (now - SUCCESS_RETENTION_SECONDS, now - PROCESSING_LEASE_SECONDS),
        )

    async def claim(self, key):
        key_hash = self._hash_key(key)
        now = time.time()
        async with self._lock:
            connection = self._connect()
            try:
                connection.execute('BEGIN IMMEDIATE')
                self._cleanup(connection, now)
                row = connection.execute(
                    '''
                    SELECT status, telegram_message_id
                    FROM telegram_deliveries
                    WHERE key_hash = ?
                    ''',
                    (key_hash,),
                ).fetchone()
                if row is not None:
                    connection.commit()
                    if row[0] == 'succeeded':
                        return ClaimResult('duplicate', row[1])
                    return ClaimResult('processing')
                connection.execute(
                    '''
                    INSERT INTO telegram_deliveries
                        (key_hash, status, telegram_message_id, processed_at)
                    VALUES (?, 'processing', NULL, ?)
                    ''',
                    (key_hash, now),
                )
                connection.commit()
                return ClaimResult('claimed')
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    async def complete(self, key, telegram_message_id):
        key_hash = self._hash_key(key)
        async with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    '''
                    UPDATE telegram_deliveries
                    SET status = 'succeeded', telegram_message_id = ?, processed_at = ?
                    WHERE key_hash = ? AND status = 'processing'
                    ''',
                    (telegram_message_id, time.time(), key_hash),
                )
                connection.commit()
            finally:
                connection.close()

    async def release(self, key):
        key_hash = self._hash_key(key)
        async with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    "DELETE FROM telegram_deliveries WHERE key_hash = ? AND status = 'processing'",
                    (key_hash,),
                )
                connection.commit()
            finally:
                connection.close()
