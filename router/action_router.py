# File: router/action_router.py

import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class ActionRouter:
    """
    Router for triggering follow-up actions based on document analysis.
    """
    
    def __init__(self, memory_store):
        self.memory_store = memory_store
        
    def route_action(self, document_id, action=None):
        """
        Route the document to the appropriate action based on analysis.
        
        Args:
            document_id (str): The ID of the document
            action (str, optional): Specific action to trigger, if provided
        
        Returns:
            dict: Result of the action
        """
        try:
            # Get document data from memory store
            document_data = self.memory_store.get(document_id)
            
            if not document_data:
                return {"success": False, "message": f"Document with ID {document_id} not found"}
            
            # Get classification and analysis data
            classification = document_data.get("data", {}).get("classification", {})
            document_format = classification.get("format")
            
            # If action is specified, use that directly
            if action:
                return self._execute_action(action, document_id, document_data)
                
            # Otherwise, determine action based on document type and analysis
            if document_format == "email":
                return self._route_email_action(document_id, document_data)
            elif document_format == "pdf":
                return self._route_pdf_action(document_id, document_data)
            elif document_format == "json":
                return self._route_json_action(document_id, document_data)
            else:
                return {"success": False, "message": f"Unsupported document format: {document_format}"}
                
        except Exception as e:
            logger.error(f"Error routing action: {e}", exc_info=True)
            return {"success": False, "message": f"Error routing action: {str(e)}"}
    
    def _route_email_action(self, document_id, document_data):
        """Route actions for email documents."""
        email_analysis = document_data.get("data", {}).get("email_analysis", {})
        
        # Determine action based on email analysis
        recommended_action = email_analysis.get("recommended_action", "")
        tone = email_analysis.get("tone", "")
        urgency = email_analysis.get("urgency", "")
        
        if recommended_action == "Escalate" or tone == "Angry" or urgency == "High":
            return self._execute_action("escalate", document_id, document_data)
        elif recommended_action == "Respond within 24 hours":
            return self._execute_action("respond", document_id, document_data)
        else:
            return self._execute_action("log", document_id, document_data)
    
    def _route_pdf_action(self, document_id, document_data):
        """Route actions for PDF documents."""
        pdf_analysis = document_data.get("data", {}).get("pdf_analysis", {})
        
        # Check for high-value invoices
        invoice_data = pdf_analysis.get("invoice_data", {})
        if invoice_data and invoice_data.get("total", 0) > 10000:
            return self._execute_action("review_invoice", document_id, document_data)
        
        # Check for policy documents with regulatory mentions
        policy_data = pdf_analysis.get("policy_data", {})
        if policy_data and policy_data.get("regulations"):
            return self._execute_action("compliance_review", document_id, document_data)
            
        # Default action for PDFs
        return self._execute_action("archive", document_id, document_data)
    
    def _route_json_action(self, document_id, document_data):
        """Route actions for JSON documents."""
        json_analysis = document_data.get("data", {}).get("json_analysis", {})
        
        # Check for anomalies or validation errors
        if not json_analysis.get("validity", {}).get("is_valid", True) or json_analysis.get("anomalies"):
            return self._execute_action("technical_review", document_id, document_data)
        
        # Default action for valid JSON
        return self._execute_action("process", document_id, document_data)
    
    def _execute_action(self, action, document_id, document_data):
        """Execute the specified action."""
        logger.info(f"Executing action '{action}' for document {document_id}")
        
        # Get metadata for logging
        metadata = document_data.get("data", {}).get("metadata", {})
        filename = metadata.get("filename", "unknown")
        
        result = {
            "action": action,
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": True
        }
        
        try:
            # Simulate API calls based on action
            if action == "escalate":
                # Simulate CRM escalation call
                result["details"] = self._simulate_api_call(
                    "POST", 
                    "/crm/escalate", 
                    {
                        "document_id": document_id,
                        "priority": "high",
                        "reason": "Customer complaint requiring immediate attention"
                    }
                )
                
            elif action == "respond":
                # Simulate response scheduling
                result["details"] = self._simulate_api_call(
                    "POST", 
                    "/crm/schedule-response", 
                    {
                        "document_id": document_id,
                        "due_within": "24 hours"
                    }
                )
                
            elif action == "review_invoice":
                # Simulate finance system notification
                result["details"] = self._simulate_api_call(
                    "POST", 
                    "/finance/review", 
                    {
                        "document_id": document_id,
                        "reason": "High-value invoice exceeding threshold"
                    }
                )
                
            elif action == "compliance_review":
                # Simulate compliance team notification
                result["details"] = self._simulate_api_call(
                    "POST", 
                    "/compliance/review", 
                    {
                        "document_id": document_id,
                        "reason": "Policy document containing regulatory references"
                    }
                )
                
            elif action == "technical_review":
                # Simulate tech team notification
                result["details"] = self._simulate_api_call(
                    "POST", 
                    "/tech/review", 
                    {
                        "document_id": document_id,
                        "reason": "JSON anomalies or validation errors"
                    }
                )
                
            elif action == "process":
                # Simulate normal processing
                result["details"] = self._simulate_api_call(
                    "POST", 
                    "/workflow/process", 
                    {"document_id": document_id}
                )
                
            elif action == "archive":
                # Simulate archiving
                result["details"] = self._simulate_api_call(
                    "POST", 
                    "/archive/store", 
                    {"document_id": document_id}
                )
                
            elif action == "log":
                # Simulate simple logging of the document
                result["details"] = {"status": "logged", "message": "Document logged for reference"}
                
            else:
                # Unknown action
                result["success"] = False
                result["message"] = f"Unknown action: {action}"
                logger.warning(f"Unknown action requested: {action}")
                return result
            
            # Store action in memory
            self.memory_store.store(document_id, "action", result)
            
            # Update document status
            self.memory_store.update_status(document_id, "action_triggered")
            
            logger.info(f"Action '{action}' executed successfully for {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing action '{action}': {e}", exc_info=True)
            result["success"] = False
            result["message"] = f"Error executing action: {str(e)}"
            return result
    
    def _simulate_api_call(self, method, endpoint, data):
        """
        Simulate an API call to an external system.
        In a real implementation, this would make actual HTTP requests.
        """
        logger.info(f"Simulating {method} call to {endpoint} with data: {data}")
        
        # In a real implementation, this would be:
        # response = requests.request(method, f"https://api.example.com{endpoint}", json=data)
        # return response.json()
        
        # For simulation, return a mock successful response
        return {
            "status": "success",
            "request_id": f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "message": f"Action submitted to {endpoint}",
            "timestamp": datetime.utcnow().isoformat()
        }