import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import Counter
from typing import Dict, List, Tuple
import re

class LinkPriortizer:
    def __init__(
        self,
        priority_rules: Dict[str, int],
        keyword_weights: Dict[str, int],
        content_type_weights: Dict[str, int]
    ) -> None:
        self.priority_rules = priority_rules
        self.keyword_weights = keyword_weights
        self.content_type_weights = content_type_weights
        self.visited_domains: Counter[str] = Counter()
        self.stop_words = set([
            'the', 'a', 'an', 'and', 'or', 'but', 
            'in', 'on', 'at', 'to', 'for', 'of', 
            'with', 'by'
        ])

    def fetch_webpage_content(self, url: str) -> str:
        """Fetch the content of a webpage and return it as a string."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            return ""

    def simple_tokenize(self, text: str) -> List[str]:
        """Tokenize a string of text into words, excluding punctuation."""
        return re.findall(r'\b\w+\b', text.lower())

    def calculate_priority(self, url: str, content: str) -> int:
        """Calculate the priority of a URL based on rules and content analysis."""
        domain = urlparse(url).netloc
        base_priority = self.priority_rules.get(domain, 0)

        text = BeautifulSoup(content, 'html.parser').get_text().lower()
        word_count = Counter(self.simple_tokenize(text))

        keyword_score = 0
        for keyword, weight in self.keyword_weights.items():
            if keyword.lower() in text:
                freq = word_count[keyword.lower()]  # Frequency of keyword
                keyword_score += freq * weight

        base_priority += keyword_score  

        path = urlparse(url).path
        for content_type, weight in self.content_type_weights.items():
            if content_type in path:
                base_priority += weight

        if self.visited_domains[domain] == 0:
            base_priority += 3
        elif self.visited_domains[domain] < 5:
            base_priority += 1

        depth = url.count('/')
        base_priority -= depth * 0.5

        return max(base_priority, 0)

    def prioritize_links(self, links: List[str]) -> List[Tuple[str, int]]:
        """Prioritize a list of links based on their calculated priority."""
        prioritized_links: List[Tuple[str, int]] = []
        for link in links:
            content = self.fetch_webpage_content(link)
            if not content:
                continue
            priority = self.calculate_priority(link, content)
            prioritized_links.append((link, priority))
            self.visited_domains[urlparse(link).netloc] += 1
        return sorted(prioritized_links, key=lambda x: x[1], reverse=True)
