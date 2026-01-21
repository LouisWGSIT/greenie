import json
import os
import threading
from typing import List, Dict
from datetime import datetime
from zoneinfo import ZoneInfo
import json


import sys
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
DEFAULT_PATH = os.path.join(BASE_DIR, "knowledge.json")

class Greenie:
    def _init_(self):
        self.name = "Greenie"

    

class KnowledgeStore:
    def __init__(self, path: str | None = None):
        self.path = path or DEFAULT_PATH
        self._lock = threading.Lock()
        if not os.path.exists(self.path):
            self._write([])

    def _read(self) -> List[Dict]:
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write(self, data: List[Dict]) -> None:
        tmp = self.path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            # If the packaged location is not writable (e.g., PyInstaller _MEIPASS),
            # fall back to writing the data to the current working directory.
            alt = os.path.join(os.getcwd(), os.path.basename(self.path))
            self.path = alt
            tmp = self.path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)

    def add_knowledge(self, name: str, description: str, keywords: List[str] = None) -> None:
        # Keep both `name` and `title` for backward compatibility with tests/older clients
        item = {"name": name, "title": name, "description": description, "keywords": keywords or []}
        with self._lock:
            data = self._read()
            data.append(item)
            self._write(data)

    def search(self, query: str, n: int = 5) -> List[Dict]:
        # naive substring search across title+content, returns top-n matches
        with self._lock:
            data = self._read()
        matches = []
        q = query.lower()
        for item in data:
            score = 0
            if q in item.get('name','').lower():
                score += 10
            if q in item.get('description','').lower():
                score += 5
            if score > 0:
                matches.append((score, item))
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:n]]

    def list_all(self) -> List[Dict]:
        return self._read()

    def best_match(self, query: str) -> Dict | None:
        """Return the single best matching knowledge item for `query`, or None."""
        with self._lock:
            data = self._read()
        q = query.lower().strip()
        best_item = None
        best_score = 0
        for item in data:
            score = 0
            if q in item.get('name','').lower():
                score += 10
            if q in item.get('description','').lower():
                score += 5
            for kw in item.get('keywords', []):
                if q in kw.lower():
                    score += 3
            if score > best_score:
                best_score = score
                best_item = item
        if best_score > 0:
            return best_item
        return None

# convenience instance for small apps
store = KnowledgeStore()


def get_time() -> dict:
    """Return current time data in UK timezone."""
    try:
        now = datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        now = datetime.now()
    human_short = now.strftime("%a %d %b %Y, %H:%M")
    return {"human_short": human_short, "iso": now.isoformat()}


def get_time_human_short() -> str:
    return get_time()["human_short"]
