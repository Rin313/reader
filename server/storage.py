# 像 localStorage 一样简单的存储层
import shelve
from contextlib import contextmanager
import os
from common import get_app_path

class ShelveStorage:
    def __init__(self, db_path: str = os.path.join(get_app_path(), "data")):
        self.db_path = db_path
    @contextmanager
    def _open(self, flag='c'):
        db = shelve.open(self.db_path, flag=flag)
        try:
            yield db
        finally:
            db.close()
    def get(self, key: str, default=None):
        with self._open('r') as db:
            return db.get(key, default)
    def set(self, key: str, value):
        with self._open() as db:
            db[key] = value
storage = ShelveStorage()