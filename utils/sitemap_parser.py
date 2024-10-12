import requests
from typing import List, Optional
from xml.etree import ElementTree as ET

class SitemapParser:
    @staticmethod
    def parse(url: str) -> Optional[List[str]]:
        try:
            response = requests.get(url)
            root = ET.fromstring(response.content)
            namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            return [loc.text for loc in root.findall('.//sm:loc', namespace) if loc.text]
        except Exception as e:
            print(f"Error parsing sitemap {url}: {str(e)}")
            return None