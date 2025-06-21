# File: agents/classifier_agent.py

import os
import logging
from datetime import datetime
import mimetypes
import re
from agents.base_agent import Agent

logger = logging.getLogger(__name__)

class ClassifierAgent(Agent):
    """
    Agent responsible for classifying document format and business intent.
    Uses file extension, MIME type, and content analysis.
    """
    
    def __init__(self, memory_store):
        super().__init__(memory_store)
    
    def classify(self, file_path, metadata, user_intent=None):
        """
        Classify the document format and business intent.
        
        Args:
            file_path (str): Path to the file to classify
            metadata (dict): Metadata about the file
            user_intent (str, optional): User-provided intent
            
        Returns:
            dict: Classification results with format, intent, and confidence
        """
        logger.info(f"Classifying document: {file_path}")
        
        try:
            # Determine file format
            format_result = self._determine_format(file_path, metadata)
            format_type = format_result["format"]
            
            # Determine business intent
            if user_intent:
                # Use user-provided intent if available
                intent = user_intent
                confidence = 1.0  # High confidence since it's user-provided
            else:
                # Auto-detect intent based on file content
                intent_result = self._determine_intent(file_path, format_type)
                intent = intent_result["intent"]
                confidence = intent_result["confidence"]
            
            # Compile classification result
            result = {
                "format": format_type,
                "intent": intent,
                "confidence": confidence
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying document: {e}", exc_info=True)
            raise
    
    def process(self, file_path, metadata):
        """
        Process method to conform to Agent abstract class.
        Just calls classify in this case.
        """
        return self.classify(file_path, metadata)
    
    def _determine_format(self, file_path, metadata):
        """Determine the format of the document."""
        # Check file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Check content type from metadata
        content_type = metadata.get("content_type", "")
        
        # Determine format based on extension and content type
        if ext == ".pdf" or content_type == "application/pdf":
            return {"format": "pdf", "confidence": 1.0}
        elif ext == ".eml" or content_type == "message/rfc822":
            return {"format": "email", "confidence": 1.0}
        elif ext == ".json" or content_type == "application/json":
            return {"format": "json", "confidence": 1.0}
        else:
            # If extension and content type don't match or are unclear,
            # perform content-based analysis
            return self._analyze_file_content(file_path)
    
    def _analyze_file_content(self, file_path):
        """Analyze file content to determine format."""
        try:
            # Read a sample of the file
            with open(file_path, 'rb') as f:
                sample = f.read(1024)  # Read first 1KB
            
            # Try to decode as text
            try:
                text_sample = sample.decode('utf-8', errors='ignore')
                
                # Check for JSON indicators
                if text_sample.strip().startswith('{') and '}' in text_sample:
                    return {"format": "json", "confidence": 0.9}
                
                # Check for email indicators
                if any(header in text_sample for header in ["From:", "To:", "Subject:", "Date:"]):
                    return {"format": "email", "confidence": 0.8}
                
            except UnicodeDecodeError:
                pass
            
            # Check for PDF signature
            if sample.startswith(b'%PDF-'):
                return {"format": "pdf", "confidence": 1.0}
            
            # Default to binary if we can't determine the format
            return {"format": "binary", "confidence": 0.5}
            
        except Exception as e:
            logger.error(f"Error analyzing file content: {e}", exc_info=True)
            return {"format": "unknown", "confidence": 0.1}
    
    def _determine_intent(self, file_path, format_type):
        """Determine the business intent of the document."""
        # Default intent and confidence
        intent = "Unknown"
        confidence = 0.5
        
        try:
            # Process based on format
            if format_type == "pdf":
                intent_result = self._analyze_pdf_intent(file_path)
            elif format_type == "email":
                intent_result = self._analyze_email_intent(file_path)
            elif format_type == "json":
                intent_result = self._analyze_json_intent(file_path)
            else:
                return {"intent": intent, "confidence": confidence}
            
            return intent_result
            
        except Exception as e:
            logger.error(f"Error determining intent: {e}", exc_info=True)
            return {"intent": intent, "confidence": confidence}
    
    def _analyze_pdf_intent(self, file_path):
        """Analyze PDF content to determine business intent."""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from first few pages for analysis
                text = ""
                for i in range(min(3, len(pdf_reader.pages))):  # First 3 pages or less
                    page = pdf_reader.pages[i]
                    text += page.extract_text() + "\n"
                
                return self._classify_text_intent(text)
                
        except Exception as e:
            logger.error(f"Error analyzing PDF intent: {e}", exc_info=True)
            return {"intent": "Unknown", "confidence": 0.1}
    
    def _analyze_email_intent(self, file_path):
        """Analyze email content to determine business intent."""
        try:
            import email
            
            with open(file_path, 'rb') as file:
                msg = email.message_from_binary_file(file)
                
                # Get subject and body for analysis
                subject = msg.get('Subject', '')
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # Combine subject and body for analysis
                text = f"{subject}\n{body}"
                return self._classify_text_intent(text)
                
        except Exception as e:
            logger.error(f"Error analyzing email intent: {e}", exc_info=True)
            return {"intent": "Unknown", "confidence": 0.1}
    
    def _analyze_json_intent(self, file_path):
        """Analyze JSON content to determine business intent."""
        try:
            import json
            
            with open(file_path, 'r') as file:
                json_data = json.load(file)
                
                # Convert JSON data to text for keyword analysis
                if isinstance(json_data, dict):
                    # Check for specific fields that might indicate intent
                    if "order" in json_data or "purchase" in json_data:
                        return {"intent": "RFQ", "confidence": 0.7}
                    elif "complaint" in json_data or "issue" in json_data:
                        return {"intent": "Complaint", "confidence": 0.7}
                    elif "invoice" in json_data or "payment" in json_data:
                        return {"intent": "Invoice", "confidence": 0.7}
                    elif "regulation" in json_data or "compliance" in json_data:
                        return {"intent": "Regulation", "confidence": 0.7}
                    elif "alert" in json_data or "fraud" in json_data:
                        return {"intent": "Fraud Risk", "confidence": 0.7}
                
                # If no specific fields, convert to string and classify
                text = json.dumps(json_data)
                return self._classify_text_intent(text)
                
        except Exception as e:
            logger.error(f"Error analyzing JSON intent: {e}", exc_info=True)
            return {"intent": "Unknown", "confidence": 0.1}
    
    def _classify_text_intent(self, text):
        """Classify business intent based on text content."""
        text_lower = text.lower()
        
        # Define intent keywords with expanded vocabulary
        intent_keywords = {
            "RFQ": ["quote", "rfq", "price", "pricing", "cost", "request for quote", "quotation", "estimate", "proposal"],
            "Complaint": ["complaint", "issue", "problem", "dissatisfied", "unhappy", "disappointed", "refund", "unacceptable"],
            "Invoice": ["invoice", "bill", "payment", "amount due", "total due", "purchase order", "remit", "paid"],
            "Regulation": ["compliance", "regulation", "policy", "requirement", "gdpr", "hipaa", "fda", "legal", "guideline"],
            "Fraud Risk": ["fraud", "suspicious", "unauthorized", "alert", "warning", "security", "breach", "risk"],
            "Order": ["order status", "shipping", "tracking", "delivery", "shipped", "order number", "expedited", "order confirmation"],
            "Report": ["report", "analysis", "quarterly", "annual", "summary", "findings", "results", "statistics", "metrics", "forecast", "trends"],
            "Resume": ["resume", "cv", "curriculum vitae", "experience", "education", "skills", "employment", "qualifications", "profile"]
        }
        
        # Count keywords for each intent with more context awareness
        intent_scores = {intent: 0 for intent in intent_keywords}
        
        # First pass - exact matches
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                count = text_lower.count(keyword)
                # Give more weight to key terms in titles/headers
                lines = text_lower.split('\n')
                for line in lines[:10]:  # Check first 10 lines for headers
                    if keyword in line and len(line) < 100:  # Likely a header/title
                        count += 1
                intent_scores[intent] += count
        
        # If this is clearly a resume, boost that score
        if any(term in text_lower for term in ["work experience", "education", "skills", "professional experience"]):
            intent_scores["Resume"] += 3
        
        # If this is clearly a report, boost that score
        if any(term in text_lower for term in ["executive summary", "key findings", "market analysis"]):
            intent_scores["Report"] += 3
        
        # Find the intent with the highest score
        max_score = max(intent_scores.values())
        if max_score == 0:
            return {"intent": "Unknown", "confidence": 0.2}
        
        top_intents = [intent for intent, score in intent_scores.items() if score == max_score]
        selected_intent = top_intents[0]  # Pick the first if there are ties
        
        # Calculate confidence based on score and uniqueness
        confidence = min(0.5 + (max_score * 0.1), 0.9)  # Scale confidence but cap at 0.9
        if len(top_intents) > 1:
            confidence *= 0.8  # Reduce confidence if there are ties
        
        return {"intent": selected_intent, "confidence": confidence}