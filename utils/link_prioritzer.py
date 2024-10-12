import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import Counter
from typing import Dict, List, Tuple
import torch
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import numpy as np

class EnhancedLinkPrioritizer:
    def __init__(
        self,
        priority_rules: Dict[str, int],
        keyword_weights: Dict[str, int],
        content_type_weights: Dict[str, int],
        target_keywords: List[str],
        model_name: str = "distilbert-base-uncased",
        sentence_model_name: str = "paraphrase-MiniLM-L6-v2"
    ):
        self.priority_rules = priority_rules
        self.keyword_weights = keyword_weights
        self.content_type_weights = content_type_weights
        self.target_keywords = target_keywords
        self.visited_domains: Counter[str] = Counter()
        
        # Initialize BERT model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        
        # Initialize Sentence Transformer
        self.sentence_transformer = SentenceTransformer(sentence_model_name)
        
        # Encode target keywords
        self.target_embedding = self.sentence_transformer.encode(" ".join(target_keywords))

    def fetch_webpage_content(self, url: str) -> str:
        """Fetch the content of a webpage and return it as a string."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            return ""

    def extract_text_from_html(self, html: str) -> str:
        """Extract text content from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ", strip=True)

    def calculate_semantic_similarity(self, text: str) -> float:
        """Calculate semantic similarity between the text and target keywords."""
        text_embedding = self.sentence_transformer.encode(text)
        return np.dot(text_embedding, self.target_embedding) / (np.linalg.norm(text_embedding) * np.linalg.norm(self.target_embedding))

    def extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from the text using BERT."""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Get the attention weights from the last layer
        attention = outputs.attentions[-1].mean(dim=1).mean(dim=1)
        
        # Get the tokens with the highest attention
        _, top_indices = attention.topk(10)
        
        # Convert token IDs back to words
        keywords = [self.tokenizer.decode([token_id]) for token_id in inputs.input_ids[0][top_indices]]
        return [kw.strip() for kw in keywords if kw.strip()]

    def calculate_priority(self, url: str, content: str) -> float:
        """Calculate the priority of a URL based on deep learning analysis."""
        domain = urlparse(url).netloc
        base_priority = float(self.priority_rules.get(domain, 0))

        text = self.extract_text_from_html(content)
        
        # Semantic similarity
        semantic_similarity = self.calculate_semantic_similarity(text)
        base_priority += semantic_similarity * 10
        
        # Keyword extraction and matching
        extracted_keywords = self.extract_keywords(text)
        keyword_score = sum(self.keyword_weights.get(kw, 0) for kw in extracted_keywords)
        base_priority += keyword_score
        
        # Content type weighting
        path = urlparse(url).path
        for content_type, weight in self.content_type_weights.items():
            if content_type in path:
                base_priority += weight
        
        # Domain diversity
        if self.visited_domains[domain] == 0:
            base_priority += 3
        elif self.visited_domains[domain] < 5:
            base_priority += 1
        
        # URL depth penalty
        depth = url.count("/")
        base_priority -= depth * 0.5
        
        return max(base_priority, 0)

    def prioritize_links(self, links: List[str]) -> List[Tuple[str, float]]:
        """Prioritize a list of links based on their calculated priority."""
        prioritized_links: List[Tuple[str, float]] = []
        for link in links:
            content = self.fetch_webpage_content(link)
            if not content:
                continue
            priority = self.calculate_priority(link, content)
            prioritized_links.append((link, priority))
            self.visited_domains[urlparse(link).netloc] += 1
        return sorted(prioritized_links, key=lambda x: x[1], reverse=True)
