# utils/nlp_utils.py
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from collections import Counter
import logging
from typing import List, Dict, Any, Tuple

# Download necessary NLTK resources
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)
except Exception as e:
    logging.warning(f"Failed to download NLTK resources: {e}")

logger = logging.getLogger(__name__)

class TextAnalyzer:
    """
    Class for advanced text analysis using NLTK.
    """
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text using NLTK.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of entities by type
        """
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "times": [],
            "money": [],
            "percentages": [],
        }
        
        try:
            # Extract named entities
            tokens = word_tokenize(text)
            pos_tags = nltk.pos_tag(tokens)
            chunks = nltk.ne_chunk(pos_tags)
            
            for chunk in chunks:
                if hasattr(chunk, 'label'):
                    entity_text = ' '.join(c[0] for c in chunk)
                    if chunk.label() == 'PERSON':
                        entities["persons"].append(entity_text)
                    elif chunk.label() == 'ORGANIZATION':
                        entities["organizations"].append(entity_text)
                    elif chunk.label() == 'GPE':  # Geo-Political Entity
                        entities["locations"].append(entity_text)
            
            # Extract dates using regex
            date_patterns = [
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # dd/mm/yyyy or dd-mm-yyyy
                r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',   # yyyy/mm/dd or yyyy-mm-dd
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'  # Month dd, yyyy
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, text, re.IGNORECASE)
                entities["dates"].extend(dates)
            
            # Extract money mentions
            money_pattern = r'\$\d+(?:\.\d+)?(?:k|m|b|mn|bn)?|\d+(?:\.\d+)? (?:dollars|USD|EUR|GBP)'
            money_mentions = re.findall(money_pattern, text)
            entities["money"].extend(money_mentions)
            
            # Extract percentages
            percentage_pattern = r'\d+(?:\.\d+)?%'
            percentages = re.findall(percentage_pattern, text)
            entities["percentages"].extend(percentages)
            
            # Deduplicate entities
            for entity_type in entities:
                entities[entity_type] = list(set(entities[entity_type]))
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
        
        return entities
    
    def extract_topics(self, text: str, num_topics: int = 5, threshold: float = 0.01) -> List[str]:
        """
        Extract main topics from text using TF-IDF-like scoring.
        This is a simplified approach without requiring additional libraries.
        
        Args:
            text: Text to analyze
            num_topics: Maximum number of topics to return
            threshold: Minimum score threshold for a word to be considered
            
        Returns:
            List of top topics/keywords
        """
        topics = []
        
        try:
            # Tokenize, remove stop words and lemmatize
            tokens = word_tokenize(text.lower())
            tokens = [self.lemmatizer.lemmatize(token) for token in tokens 
                     if token.isalnum() and token not in self.stop_words]
            
            # Count word frequencies
            word_counts = Counter(tokens)
            total_words = len(tokens)
            
            # Calculate scores (similar to TF-IDF but without IDF)
            word_scores = {}
            for word, count in word_counts.items():
                if len(word) > 2:  # Ignore very short words
                    word_scores[word] = count / total_words
            
            # Filter by threshold and get top N
            topics = [word for word, score in sorted(word_scores.items(), 
                                                    key=lambda x: x[1], 
                                                    reverse=True) 
                     if score > threshold][:num_topics]
            
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
        
        return topics
    
    def calculate_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Simple rule-based sentiment analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        sentiment = {
            "score": 0.0,
            "magnitude": 0.0,
            "assessment": "neutral"
        }
        
        try:
            # Simple positive and negative word lists
            positive_words = set([
                'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
                'terrific', 'outstanding', 'superb', 'brilliant', 'awesome', 
                'impressive', 'remarkable', 'positive', 'nice', 'love', 'happy',
                'satisfied', 'pleased', 'enjoy', 'beneficial', 'successful'
            ])
            
            negative_words = set([
                'bad', 'poor', 'terrible', 'awful', 'horrible', 'dreadful',
                'unpleasant', 'disappointing', 'negative', 'sad', 'angry',
                'upset', 'unhappy', 'hate', 'dislike', 'awful', 'mediocre',
                'inferior', 'substandard', 'problem', 'issue', 'error', 'fault',
                'failure', 'defect', 'mistake', 'unfortunate'
            ])
            
            # Tokenize and lemmatize
            tokens = word_tokenize(text.lower())
            lemmas = [self.lemmatizer.lemmatize(token) for token in tokens if token.isalpha()]
            
            # Count sentiment words
            positive_count = sum(1 for word in lemmas if word in positive_words)
            negative_count = sum(1 for word in lemmas if word in negative_words)
            
            # Calculate score and magnitude
            total_words = len(lemmas)
            if total_words > 0:
                sentiment["score"] = (positive_count - negative_count) / total_words
                sentiment["magnitude"] = (positive_count + negative_count) / total_words
                
                # Determine assessment
                if sentiment["score"] > 0.05:
                    sentiment["assessment"] = "positive"
                elif sentiment["score"] < -0.05:
                    sentiment["assessment"] = "negative"
                else:
                    sentiment["assessment"] = "neutral"
            
        except Exception as e:
            logger.error(f"Error calculating sentiment: {e}")
        
        return sentiment
    
    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """
        Extract key sentences as a summary.
        
        Args:
            text: Text to summarize
            max_sentences: Maximum number of sentences to include
            
        Returns:
            Summary text
        """
        summary = ""
        
        try:
            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            if len(sentences) <= max_sentences:
                return text
                
            # Score sentences based on position and length
            sentence_scores = []
            for i, sentence in enumerate(sentences):
                # Position score - beginning and end sentences often contain key info
                position_score = 1.0
                if i == 0 or i == len(sentences) - 1:
                    position_score = 2.0
                
                # Length score - very short or very long sentences are less likely to be key
                words = len(sentence.split())
                length_score = 1.0
                if 5 <= words <= 20:
                    length_score = 1.5
                
                sentence_scores.append((i, sentence, position_score * length_score))
            
            # Select top sentences
            top_sentences = sorted(sentence_scores, key=lambda x: x[2], reverse=True)[:max_sentences]
            
            # Reconstruct summary in original order
            summary_sentences = sorted(top_sentences, key=lambda x: x[0])
            summary = ' '.join(s[1] for s in summary_sentences)
            
        except Exception as e:
            logger.error(f"Error summarizing text: {e}")
            summary = text[:200] + "..."  # Fallback to simple truncation
        
        return summary

analyzer = TextAnalyzer()