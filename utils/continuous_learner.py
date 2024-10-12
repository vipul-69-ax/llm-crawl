from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from typing import List

class ContinuousLearner:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.classifier = MultinomialNB()
        self.is_trained = False

    def train(self, texts: List[str], labels: List[int]):
        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)
        self.is_trained = True

    def predict(self, text: str) -> float:
        if not self.is_trained:
            return 0.5
        X = self.vectorizer.transform([text])
        return self.classifier.predict_proba(X)[0][1]

    def update(self, text: str, label: int):
        if not self.is_trained:
            self.train([text], [label])
        else:
            X = self.vectorizer.transform([text])
            self.classifier.partial_fit(X, [label])