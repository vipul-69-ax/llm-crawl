import hashlib
from typing import Set

class ContentDeduplicator:
    def __init__(self):
        self.content_hashes: Set[str] = set()

    def is_duplicate(self, content: str) -> bool:
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self.content_hashes:
            return True
        self.content_hashes.add(content_hash)
        return False