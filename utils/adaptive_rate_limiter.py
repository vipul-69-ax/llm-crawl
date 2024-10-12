import time
from collections import defaultdict
from typing import Dict

class AdaptiveRateLimiter:
    def __init__(self, initial_delay: float = 1.0, backoff_factor: float = 1.5, max_delay: float = 60.0):
        self.delays: Dict[str, float] = defaultdict(lambda: initial_delay)
        self.last_request_time: Dict[str, float] = defaultdict(float)
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    def wait(self, domain: str):
        current_time = time.time()
        elapsed = current_time - self.last_request_time[domain]
        if elapsed < self.delays[domain]:
            time.sleep(self.delays[domain] - elapsed)
        self.last_request_time[domain] = time.time()

    def update(self, domain: str, success: bool):
        if success:
            self.delays[domain] = max(self.delays[domain] / self.backoff_factor, 1.0)
        else:
            self.delays[domain] = min(self.delays[domain] * self.backoff_factor, self.max_delay)