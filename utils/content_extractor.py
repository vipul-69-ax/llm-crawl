from newspaper import Article
from typing import Dict, Optional

class ContentExtractor:
    @staticmethod
    def extract(html: str, url: str) -> Optional[Dict[str, str]]:
        try:
            article = Article(url)
            article.set_html(html)
            article.parse()
            return {
                "title": article.title,
                "text": article.text,
                "summary": article.summary,
                "keywords": article.keywords,
                "authors": article.authors,
                "publish_date": str(article.publish_date) if article.publish_date else None,
            }
        except Exception as e:
            print(f"Error extracting content from {url}: {str(e)}")
            return None