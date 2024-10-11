import heapq
from typing import List, Dict, Callable, Optional, Tuple
import requests
from bs4 import BeautifulSoup
import validators
from link_prioritze import LinkPriortizer
import random
from pydantic import BaseModel

class FrontierItem(BaseModel):
    tuple[int, str]

class Crawler:
    def __init__(
        self,
        init_frontier: List[FrontierItem],
        priority_rules: Dict[str, int],
        keyword_weights: Dict[str, int],
        content_type_weights: Dict[str, int],
        priority_retention: int,
        parse_callback: Optional[Callable[[str], str]] = None,
        output_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.priority_rules = priority_rules
        self.keyword_weights = keyword_weights
        self.content_type_weights = content_type_weights
        self.priority_retention = priority_retention
        self.parse_callback = parse_callback
        self.output_callback = output_callback
        self.frontier: List[Tuple[int, str]] = []
        if init_frontier:
            for item in init_frontier:
                heapq.heappush(self.frontier, (-item[0], item[1]))

    def get_frontier_queue(self) -> List[Tuple[int, str]]:
        return self.frontier

    def push_frontier(self, item: FrontierItem) -> None:
        heapq.heappush(self.frontier, (-item[0], item[1]))

    def fetch_page(self, item: FrontierItem) -> Optional[str]:
        url = item[1]
        try:
            response = requests.get(url)
            return response.text
        except Exception:
            return None

    def add_links_to_frontier(self, response_html: str) -> None:
        soup = BeautifulSoup(response_html, "html.parser")
        links: set[str] = set()
        for a in soup.find_all("a", href=True):
            if validators.url(a["href"]):
                links.add(a["href"])
        links_list = list(links)
        prioritizer = LinkPriortizer(
            self.priority_rules, self.keyword_weights, self.content_type_weights
        )
        prioritized_links = prioritizer.prioritize_links(links_list)
        prioritized_links = prioritized_links[:self.priority_retention]
        for link, priority in prioritized_links:
            self.push_frontier((priority, link))

    def parse_content(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        main_content = soup.find("main") or soup.find("article") or soup.body

        if main_content:
            text = main_content.get_text(separator=" ", strip=True)
        else:
            text = soup.get_text(separator=" ", strip=True)

        return " ".join(text.split())

    def start_crawl(self) -> None:
        file_path = f"{f'{random.random()}'.replace('.', 'x')}.txt"
        while len(self.frontier) > 0:
            frontier_item = heapq.heappop(self.frontier)
            response = self.fetch_page(frontier_item)
            if response is None:
                continue
            else:
                self.add_links_to_frontier(response)
                content: Optional[str] = None
                if self.parse_callback is not None:
                    content = self.parse_callback(response)
                else:
                    content = self.parse_content(response)

                if content is not None:
                    if self.output_callback is None:
                        with open(file_path, 'a', encoding='utf-8') as file:
                            file.write(content + "\n")
                    else:
                        self.output_callback(content)
