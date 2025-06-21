# File: agents/email_agent.py

import os
import email
import logging
import re
from datetime import datetime
from agents.base_agent import Agent

logger = logging.getLogger(__name__)

class EmailAgent(Agent):
    """
    Agent specialized in processing email files.
    Extracts structured fields, identifies tone and urgency,
    and recommends actions based on analysis.
    """
    
    def __init__(self, memory_store):
        super().__init__(memory_store)
        
    def process(self, file_path, metadata):
        """Process an email file and extract relevant information."""
        logger.info(f"Processing email file: {file_path}")
        
        try:
            # Parse the email file
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f)
            
            # Extract basic email fields
            sender = msg.get('From', 'Unknown')
            recipient = msg.get('To', 'Unknown')
            subject = msg.get('Subject', 'No Subject')
            date = msg.get('Date', 'Unknown')
            
            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Analyze the content to determine email type, tone, and urgency
            email_type = self._determine_email_type(subject, body)
            tone = self._analyze_tone(subject, body)
            urgency = self._determine_urgency(subject, body)
            
            # Generate a summary of the email
            summary = self._generate_summary(subject, body)
            
            # Determine recommended action based on tone, urgency and type
            recommended_action = self._recommend_action(tone, urgency, email_type)
            
            # Create the analysis result
            result = {
                "email_type": email_type,
                "sender": sender,
                "recipient": recipient,
                "subject": subject,
                "date": date,
                "tone": tone,
                "urgency": urgency,
                "summary": summary,
                "recommended_action": recommended_action
            }
            
            # Store the results in memory
            document_id = metadata["document_id"]
            self.memory_store.store(document_id, "email_analysis", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)
            raise
    
    def _determine_email_type(self, subject, body):
        """Determine the type of email based on content analysis."""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        # Check for complaint indicators
        if any(term in subject_lower or term in body_lower for term in 
               ["complaint", "issue", "problem", "dissatisfied", "unhappy", 
                "disappointed", "refund", "unacceptable", "terrible"]):
            return "Complaint"
        
        # Check for inquiry indicators
        elif any(term in subject_lower or term in body_lower for term in 
                ["inquiry", "question", "information", "details", "help"]):
            return "Inquiry"
        
        # Check for RFQ indicators
        elif any(term in subject_lower or term in body_lower for term in 
                ["quote", "quotation", "rfq", "price", "pricing", "cost"]):
            return "RFQ"
        
        # Check for order-related indicators
        elif any(term in subject_lower or term in body_lower for term in 
                ["order", "purchase", "shipping", "delivery", "tracking"]):
            return "Order-related"
        
        # Default type
        return "General"
    
    def _analyze_tone(self, subject, body):
        """Analyze the tone of the email."""
        combined_text = (subject + " " + body).lower()
        
        # Check for angry/upset indicators
        angry_terms = ["angry", "furious", "outraged", "frustrated", "upset", 
                      "terrible", "horrible", "unacceptable", "disappointed",
                      "ridiculous", "worst", "awful", "never"]
        angry_count = sum(1 for term in angry_terms if term in combined_text)
        
        # Check for urgent indicators
        urgent_terms = ["urgent", "immediately", "asap", "emergency", "critical",
                       "right now", "promptly", "quickly", "expedite", "rush"]
        urgent_count = sum(1 for term in urgent_terms if term in combined_text)
        
        # Check for polite indicators
        polite_terms = ["please", "thank", "appreciate", "grateful", "kind", 
                       "regards", "sincerely", "respectfully"]
        polite_count = sum(1 for term in polite_terms if term in combined_text)
        
        # Exclamation marks and all caps words are indicators of emotions
        exclamation_count = combined_text.count("!")
        caps_words = sum(1 for word in combined_text.split() if word.isupper() and len(word) > 2)
        
        # Determine tone based on indicators
        if angry_count > 2 or exclamation_count > 3 or caps_words > 3:
            return "Angry"
        elif urgent_count > 2:
            return "Urgent"
        elif polite_count > 2:
            return "Polite"
        else:
            return "Neutral"
    
    def _determine_urgency(self, subject, body):
        """Determine the urgency level of the email."""
        combined_text = (subject + " " + body).lower()
        
        # High urgency indicators - use whole phrases to avoid false positives
        high_urgency = ["urgent", "immediately", "asap", "emergency", "critical",
                      "right now", "right away"]
        
        # Medium urgency indicators
        medium_urgency = ["soon", "timely", "attention", "priority", "follow up",
                        "response needed", "please respond", "update", "need by", 
                        "as soon as possible"]
        
        # Check for urgency indicators - use more precise phrase matching
        high_count = 0
        for term in high_urgency:
            if term in combined_text:
                high_count += 1
                
        medium_count = 0
        for term in medium_urgency:
            if term in combined_text:
                medium_count += 1
        
        exclamation_count = combined_text.count("!")
        
        # Determine urgency level with adjusted thresholds
        if "urgent" in subject.lower() or exclamation_count > 3 or "emergency" in combined_text:
            return "High"
        elif high_count >= 1:  # Stricter threshold for high urgency
            return "High"
        elif medium_count >= 1 or exclamation_count >= 1:
            return "Medium"
        else:
            return "Low"
    
    def _generate_summary(self, subject, body):
        """Generate a summary of the email content."""
        # Simple summary for now - first line and subject
        first_line = body.strip().split('\n')[0].strip() if body.strip() else ""
        
        if len(first_line) > 10:  # Ensure first line is substantial
            summary = f"This is a {self._determine_email_type(subject, body).lower()} email with subject '{subject}'. It begins with: {first_line}"
            
            # Add additional context based on body content
            if "order" in body.lower():
                order_match = re.search(r'#\d+', body)
                order_number = order_match.group(0) if order_match else "unknown order number"
                summary += f" The email refers to order {order_number}."
                
            if "refund" in body.lower():
                summary += " The sender is requesting a refund."
                
            if "help" in body.lower():
                summary += " The sender is asking for assistance."
        else:
            # Fallback if first line is too short
            summary = f"This is a {self._determine_email_type(subject, body).lower()} email with subject '{subject}'. The email is regarding "
            
            if "order" in body.lower():
                summary += "an order issue."
            elif "payment" in body.lower():
                summary += "a payment concern."
            elif "inquiry" in body.lower() or "question" in body.lower():
                summary += "a customer inquiry."
            else:
                summary += f"a {self._determine_email_type(subject, body).lower()} matter."
        
        return summary
    
    def _recommend_action(self, tone, urgency, email_type):
        """Recommend action based on email tone, urgency and type."""
        # Handle order-related emails specifically
        if email_type == "Order-related":
            return "Process routinely"
        # Other email types follow urgency/tone rules
        elif tone == "Angry" or urgency == "High" or email_type == "Complaint":
            return "Escalate"
        elif email_type == "Inquiry" or email_type == "RFQ":
            return "Respond within 24 hours"
        else:
            return "Log and review"