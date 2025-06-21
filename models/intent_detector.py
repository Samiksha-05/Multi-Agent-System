# File: models/intent_detector.py (or wherever your intent detection logic is)

import json
import logging
from models.classifier import IntentClassifier

logger = logging.getLogger(__name__)

class IntentDetector:
    """
    Detects the intent of documents.
    """
    
    def __init__(self, classifier_model=None):
        """
        Initialize the intent detector.
        
        Args:
            classifier_model: Pre-trained classifier model (optional)
        """
        self.classifier = classifier_model if classifier_model else IntentClassifier()
    
    def detect_intent(self, file_path, content_type, text_content=None):
        """
        Detect the intent of a document.
        
        Args:
            file_path: Path to the document file
            content_type: MIME type of the document
            text_content: Pre-extracted text content (optional)
            
        Returns:
            dict: Intent classification results
        """
        try:
            # Special handling for JSON files
            if content_type == 'application/json':
                # Try to detect JSON schema specifically
                json_intent = self._detect_json_intent(file_path)
                if json_intent:
                    return json_intent
            
            # Default intent classification
            intent, confidence = self.classifier.classify(file_path, content_type, text_content)
            
            return {
                "intent": intent,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error detecting intent: {e}", exc_info=True)
            return {
                "intent": "Unknown",
                "confidence": 0.1  # Low confidence for error cases
            }
    
    def _detect_json_intent(self, file_path):
        """
        Special handling for JSON files to detect schema files.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            dict: Intent classification results, or None if not a special JSON type
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            try:
                json_data = json.loads(content)
                
                # Check if this is a JSON schema file
                if isinstance(json_data, dict):
                    # Look for schema indicators
                    schema_indicators = [
                        "$schema" in json_data,
                        "properties" in json_data,
                        "type" in json_data and json_data.get("type") == "object",
                        "required" in json_data and isinstance(json_data.get("required"), list),
                        "definitions" in json_data
                    ]
                    
                    # If multiple schema indicators are found, it's likely a schema
                    if sum(schema_indicators) >= 2:
                        return {
                            "intent": "Schema Definition",
                            "confidence": 0.85
                        }
                    
                    # Check for config file indicators
                    config_indicators = [
                        "config" in file_path.lower(),
                        "settings" in file_path.lower(),
                        "environment" in json_data,
                        "configuration" in json_data,
                        "api_key" in str(json_data).lower(),
                        "host" in json_data and "port" in json_data
                    ]
                    
                    if sum(config_indicators) >= 2:
                        return {
                            "intent": "Configuration",
                            "confidence": 0.80
                        }
                    
                    # Check for data structure
                    if len(json_data) > 0 and all(isinstance(v, (dict, list)) for v in json_data.values()):
                        has_items = False
                        for v in json_data.values():
                            if isinstance(v, list) and len(v) > 0:
                                has_items = True
                                break
                        
                        if has_items:
                            return {
                                "intent": "Data Structure",
                                "confidence": 0.75
                            }
            except:
                # If there's a parsing error, it's likely an invalid JSON
                # We'll return None and let the default classifier handle it
                pass
                
            return None
                
        except Exception as e:
            logger.error(f"Error in JSON intent detection: {e}", exc_info=True)
            return None