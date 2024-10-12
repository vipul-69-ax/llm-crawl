import asyncio
import aiohttp
from typing import List, Dict, Tuple
from urllib.parse import urlparse
import logging
from tqdm import tqdm
import time
from celery import Celery
import os
from bs4 import BeautifulSoup
import json

from utils.adaptive_rate_limiter import AdaptiveRateLimiter
from utils.content_extractor import ContentExtractor
from utils.sitemap_parser import SitemapParser
from utils.robots_parser import RobotsParser
from utils.proxy_manager import ProxyManager
from utils.content_deduplicator import ContentDeduplicator
from utils.continuous_learner import ContinuousLearner
from utils.link_prioritzer import EnhancedLinkPrioritizer

# Celery configuration
celery_app = Celery(
    "crawler_tasks",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),
)
celery_app.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)


class EnhancedCrawler:
    def __init__(
        self,
        seed_urls: List[str],
        config: Dict,
        max_depth: int = 3,
        max_urls_per_domain: int = 100,
        user_agent: str = "EnhancedCrawlerBot/1.0",
        output_file: str = "crawl_results.json",
    ):
        self.seed_urls = seed_urls
        self.config = config
        self.max_depth = max_depth
        self.max_urls_per_domain = max_urls_per_domain
        self.user_agent = user_agent
        self.output_file = output_file

        self.rate_limiter = AdaptiveRateLimiter()
        self.content_extractor = ContentExtractor()
        self.sitemap_parser = SitemapParser()
        self.robots_parser = RobotsParser()
        self.proxy_manager = ProxyManager(config.get("proxies", []))
        self.content_deduplicator = ContentDeduplicator()
        self.continuous_learner = ContinuousLearner()
        self.link_prioritizer = EnhancedLinkPrioritizer(
            config["priority_rules"],
            config["keyword_weights"],
            config["content_type_weights"],
            config["target_keywords"],
        )

        self.visited_urls: set = set()
        self.url_queue: List[Tuple[str, int]] = [(url, 0) for url in seed_urls]
        self.results: List[Dict] = []

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def crawl(self):
        async with aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent}
        ) as session:
            tasks = [
                self.process_url(session, url, depth) for url, depth in self.url_queue
            ]
            await asyncio.gather(*tasks)

    async def process_url(self, session: aiohttp.ClientSession, url: str, depth: int):
        if depth > self.max_depth or url in self.visited_urls:
            return

        domain = urlparse(url).netloc
        if (
            sum(1 for u in self.visited_urls if urlparse(u).netloc == domain)
            >= self.max_urls_per_domain
        ):
            return

        if not self.robots_parser.can_fetch(url, self.user_agent):
            self.logger.info(f"Skipping {url} as per robots.txt rules")
            return

        self.rate_limiter.wait(domain)
        proxy = self.proxy_manager.get_proxy()

        try:
            async with session.get(url, proxy=proxy) as response:
                if response.status == 200:
                    content = await response.text()
                    if not self.content_deduplicator.is_duplicate(content):
                        extracted_content = self.content_extractor.extract(content, url)
                        if extracted_content:
                            relevance_score = self.continuous_learner.predict(
                                extracted_content["text"]
                            )
                            extracted_content["relevance_score"] = relevance_score
                            extracted_content["url"] = url
                            self.results.append(extracted_content)

                            # Update the continuous learner
                            self.continuous_learner.update(
                                extracted_content["text"], int(relevance_score > 0.5)
                            )

                            # Extract and prioritize links
                            soup = BeautifulSoup(content, "html.parser")
                            links = [a["href"] for a in soup.find_all("a", href=True)]
                            prioritized_links = self.link_prioritizer.prioritize_links(
                                links
                            )

                            for link, priority in prioritized_links:
                                full_url = (
                                    urlparse(link).scheme
                                    and link
                                    or f"{urlparse(url).scheme}://{urlparse(url).netloc}{link}"
                                )
                                if full_url not in self.visited_urls:
                                    self.url_queue.append((full_url, depth + 1))

                    self.visited_urls.add(url)
                    self.rate_limiter.update(domain, True)
                else:
                    self.logger.warning(
                        f"Failed to fetch {url}: HTTP {response.status}"
                    )
                    self.rate_limiter.update(domain, False)

        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            self.rate_limiter.update(domain, False)

    async def start(self):
        start_time = time.time()
        with tqdm(total=len(self.seed_urls), desc="Crawling Progress") as pbar:
            await self.crawl()
            pbar.update(len(self.visited_urls))

        self.logger.info(
            f"Crawling completed. Total URLs crawled: {len(self.visited_urls)}"
        )
        self.logger.info(f"Total time: {time.time() - start_time:.2f} seconds")

        # Store results in a file
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Results stored in {self.output_file}")

    @celery_app.task
    def crawl_url_task(url: str, depth: int, config: Dict) -> List[str]:
        crawler = EnhancedCrawler([url], config, max_depth=1)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(crawler.crawl())
        return [result["url"] for result in crawler.results]

    def run_distributed(self):
        tasks = [
            self.crawl_url_task.delay(url, 0, self.config) for url in self.seed_urls
        ]
        results = []

        while tasks:
            new_tasks = []
            for task in tasks:
                if task.ready():
                    result = task.get()
                    results.extend(result)
                    if len(results) < self.max_depth * len(self.seed_urls):
                        new_tasks.extend(
                            [
                                self.crawl_url_task.delay(
                                    url, task.depth + 1, self.config
                                )
                                for url in result
                            ]
                        )
                else:
                    new_tasks.append(task)
            tasks = new_tasks

        return results

