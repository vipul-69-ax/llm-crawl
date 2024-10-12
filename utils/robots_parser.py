from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

class RobotsParser:
    def __init__(self):
        self.parsers = {}

    def can_fetch(self, url: str, user_agent: str) -> bool:
        domain = urlparse(url).netloc
        if domain not in self.parsers:
            robots_url = f"https://{domain}/robots.txt"
            parser = RobotFileParser(robots_url)
            parser.read()
            self.parsers[domain] = parser
        return self.parsers[domain].can_fetch(user_agent, url)