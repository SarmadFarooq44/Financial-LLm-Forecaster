import torch
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer

class DecisionAgent:
    def __init__(self, sentiment_threshold=0.2):
        """
        Initialize the DecisionAgent with a sentiment threshold.

        :param sentiment_threshold: Threshold for deciding buy/sell/hold.
        """
        self.sentiment_threshold = sentiment_threshold
        self.model_name = "yiyanghkust/finbert-tone"

        # Load FinBERT model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)

        # Initialize sentiment analysis pipeline
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis", model=self.model, tokenizer=self.tokenizer
        )

    def analyze_sentiment(self, text):
        """
        Analyze the sentiment of the given text using FinBERT.

        :param text: Text to analyze (str)
        :return: Sentiment score (float)
        """
        try:
            max_length = 500  # Explicitly set maximum length to 500
            tokens = self.tokenizer(text, truncation=False, return_tensors="pt")["input_ids"].squeeze(0)

            # Ensure chunks fit within max length
            chunks = [
                tokens[i:i + max_length - 2]
                for i in range(0, len(tokens), max_length - 2)
            ]

            total_score = 0
            valid_chunks = 0

            for idx, chunk in enumerate(chunks):
                # Decode chunk back to text
                chunk_text = self.tokenizer.decode(chunk, skip_special_tokens=True)
                print(f"Processing Chunk {idx + 1}: {len(chunk)} tokens")

                # Use pipeline on the chunk
                try:
                    results = self.sentiment_pipeline(chunk_text)
                    print(f"Sentiment Results for Chunk {idx + 1}: {results}")

                    label = results[0]["label"]
                    score = results[0]["score"]

                    if label == "Positive":
                        total_score += score
                    elif label == "Negative":
                        total_score -= score

                    # Count all chunks as valid regardless of label
                    valid_chunks += 1
                except Exception as e:
                    print(f"Error processing chunk {idx + 1}: {e}")

            # Compute average sentiment score
            average_score = total_score / valid_chunks if valid_chunks else 0
            return average_score
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return 0

    def analyze_article(self, article, article_index):
        """
        Analyze a single article to determine its sentiment and relevance.

        :param article: A dictionary containing article headline, content, and metadata.
        :param article_index: Index of the article in the list for identification.
        :return: Sentiment score and relevance score.
        """
        try:
            # Use content if available; fallback to title
            text_to_analyze = article.get('content') or article.get('title')
            if not text_to_analyze:
                print(f"Skipping article {article_index} due to missing content or title: {article}")
                return 0, 0

            sentiment_score = self.analyze_sentiment(text_to_analyze, article_index)
            relevance_score = 1.0  # Assume relevance is high for all articles
            return sentiment_score, relevance_score
        except Exception as e:
            print(f"Error analyzing article {article_index}: {e}")
            return 0, 0

    def analyze_sentiment(self, text, article_index):
        """
        Analyze the sentiment of the given text using FinBERT.

        :param text: Text to analyze (str)
        :param article_index: Index of the article in the list for identification.
        :return: Sentiment score (float)
        """
        try:
            max_length = 500  # Explicitly set maximum length to 500
            tokens = self.tokenizer(text, truncation=False, return_tensors="pt")["input_ids"].squeeze(0)

            # Ensure chunks fit within max length
            chunks = [
                tokens[i:i + max_length - 2]
                for i in range(0, len(tokens), max_length - 2)
            ]

            total_score = 0
            valid_chunks = 0

            for idx, chunk in enumerate(chunks):
                # Decode chunk back to text
                chunk_text = self.tokenizer.decode(chunk, skip_special_tokens=True)
                print(f"Processing Chunk {idx + 1} from Article {article_index}: {len(chunk)} tokens")

                # Use pipeline on the chunk
                try:
                    results = self.sentiment_pipeline(chunk_text)
                    print(f"Sentiment Results for Chunk {idx + 1} from Article {article_index}: {results}")

                    label = results[0]["label"]
                    score = results[0]["score"]

                    if label == "Positive":
                        total_score += score
                    elif label == "Negative":
                        total_score -= score

                    # Count all chunks as valid regardless of label
                    valid_chunks += 1
                except Exception as e:
                    print(f"Error processing chunk {idx + 1} from Article {article_index}: {e}")

            # Compute average sentiment score
            average_score = total_score / valid_chunks if valid_chunks else 0
            return average_score
        except Exception as e:
            print(f"Error analyzing sentiment for Article {article_index}: {e}")
            return 0

    def make_decision(self, articles):
        """
        Make a buy/sell/hold decision based on the sentiment of financial articles.

        :param articles: List of dictionaries containing article data.
        :return: Decision and sentiment summary.
        """
        if not articles:
            return {
                "decision": "HOLD",
                "average_sentiment": 0,
                "articles_analyzed": 0
            }

        total_sentiment = 0
        valid_articles = 0

        for article_index, article in enumerate(articles, start=1):
            sentiment_score, _ = self.analyze_article(article, article_index)
            total_sentiment += sentiment_score

            # Count all articles as analyzed
            valid_articles += 1

        if valid_articles == 0:
            return {
                "decision": "HOLD",
                "average_sentiment": 0,
                "articles_analyzed": 0
            }

        average_sentiment = total_sentiment / valid_articles

        if average_sentiment > self.sentiment_threshold:
            decision = "BUY"
        elif average_sentiment < -self.sentiment_threshold:
            decision = "SELL"
        else:
            decision = "HOLD"

        print(f"Final Decision: {decision}, Average Sentiment: {average_sentiment}, Articles Analyzed: {valid_articles}")
        return {
            "decision": decision,
            "average_sentiment": average_sentiment,
            "articles_analyzed": valid_articles
        }
