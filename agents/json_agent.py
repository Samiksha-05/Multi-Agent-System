# File: agents/json_agent.py

import json
import logging
import os
import re
from datetime import datetime
from agents.base_agent import Agent

logger = logging.getLogger(__name__)

class JsonAgent(Agent):
    """
    Agent specialized in processing JSON files.
    """
    
    def __init__(self, memory_store):
        super().__init__(memory_store)
    
    def process(self, file_path, metadata):
        """Process a JSON file and extract relevant information."""
        logger.info(f"Processing JSON file: {file_path}")
        
        try:
            # Initialize result structure to match template expectations
            result = {
                # Top level fields
                "json_type": "Generic JSON",
                "summary": "",
                
                # Nested objects exactly as expected by template
                "validity": {
                    "is_valid": False,
                    "errors": []
                },
                "structure": {
                    "complexity": "Medium",
                    "fields_count": 0
                },
                "anomalies": []
            }
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
                
            # Try to parse the JSON
            json_data = {}
            error_context = ""
            try:
                json_data = json.loads(file_content)
                result["validity"]["is_valid"] = True
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error: {str(e)}")
                
                # Format error message
                error_message = f"JSON syntax error: {str(e)}"
                result["validity"]["errors"].append(error_message)
                
                # Get error context
                lines = file_content.split('\n')
                if hasattr(e, 'lineno') and e.lineno <= len(lines):
                    error_line = lines[e.lineno - 1]
                    error_context = f"near: {error_line.strip()}"
                    result["validity"]["errors"].append(error_context)
                
                # Generate summary for invalid JSON
                result["summary"] = f"This is an invalid JSON document with syntax errors. Error context: {error_context}"
            
            # Determine document intent and type
            # For invalid JSON, we'll try to infer from the text content
            intent_info = self._determine_document_intent(
                json_data, 
                file_path, 
                metadata.get("filename", ""),
                is_valid=result["validity"]["is_valid"],
                raw_content=file_content
            )
            
            # Only perform detailed analysis if JSON is valid
            if result["validity"]["is_valid"]:
                # Determine JSON type
                result["json_type"] = intent_info["document_type"]
                
                # Count fields
                result["structure"]["fields_count"] = self._count_fields(json_data)
                
                # Determine complexity
                result["structure"]["complexity"] = self._determine_complexity(json_data)
                
                # Check for anomalies
                anomalies = self._detect_anomalies(json_data)
                if anomalies:
                    for anomaly in anomalies:
                        result["anomalies"].append({
                            "type": "Data Issue",
                            "message": anomaly
                        })
                
                # Generate summary
                result["summary"] = f"This is a {result['json_type']} with {result['structure']['fields_count']} total fields."
            
            # Log the result for debugging
            logger.info(f"JSON analysis completed with result structure: {result}")
            
            # Store the results
            document_id = metadata.get("document_id", "unknown")
            self.memory_store.store(document_id, "json_analysis", result)
            
            # Update the classification with the detected intent
            updated_classification = {
                "format": "json",
                "intent": intent_info["intent"],
                "confidence": intent_info["confidence"]
            }
            self.memory_store.store(document_id, "classification", updated_classification)
            logger.info(f"Updated classification for JSON document: {updated_classification}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing JSON: {e}", exc_info=True)
            
            # Return error result that matches expected structure
            return {
                "json_type": "Generic JSON",
                "summary": f"Error processing JSON file: {str(e)}",
                "validity": {
                    "is_valid": False,
                    "errors": [f"Processing error: {str(e)}"]
                },
                "structure": {
                    "complexity": "Unknown",
                    "fields_count": 0
                },
                "anomalies": []
            }
    
    def _determine_document_intent(self, json_data, file_path, filename, is_valid=True, raw_content=""):
        """
        Determine both the document intent and JSON type based on content and filename.
        For invalid JSON, we try to infer from the raw content string.
        
        Returns:
            dict: containing intent, confidence, and document_type keys
        """
        # Default result
        result = {
            "intent": "Unknown",
            "confidence": 0.2,
            "document_type": "Generic JSON"
        }
        
        # For invalid JSON, try to infer from raw content
        if not is_valid and raw_content:
            # Use regex to find key patterns even in invalid JSON
            return self._infer_from_raw_content(raw_content, filename)
            
        if not isinstance(json_data, dict) or not json_data:
            return result
            
        # Check for schema
        schema_indicators = [
            "$schema" in json_data,
            "properties" in json_data and isinstance(json_data.get("properties"), dict),
            "type" in json_data and json_data.get("type") == "object",
            "required" in json_data and isinstance(json_data.get("required"), list),
            "definitions" in json_data,
            "schema" in filename.lower()
        ]
        
        schema_confidence = sum(schema_indicators) * 0.15
        if schema_confidence >= 0.3:
            return {
                "intent": "Schema Definition",
                "confidence": min(0.9, schema_confidence),
                "document_type": "Schema Definition"
            }
            
        # Check for configuration
        config_indicators = [
            "config" in filename.lower(),
            "settings" in filename.lower(),
            "environment" in json_data,
            "config" in json_data,
            "settings" in json_data,
            "configuration" in json_data,
            "database" in json_data,
            "server" in json_data,
            "host" in json_data,
            "port" in json_data,
            "api" in json_data and "key" in json_data,
            "features" in json_data
        ]
        
        config_confidence = sum(config_indicators) * 0.1
        if config_confidence >= 0.2:
            return {
                "intent": "Configuration",
                "confidence": min(0.85, config_confidence),
                "document_type": "Configuration"
            }
            
        # Check for data structure
        data_structure_indicators = [
            "data" in filename.lower(),
            "items" in json_data and isinstance(json_data.get("items"), list) and len(json_data.get("items", [])) > 0,
            "records" in json_data,
            "results" in json_data,
            "list" in json_data,
            len([k for k, v in json_data.items() if isinstance(v, list) and len(v) > 0]) > 0
        ]
        
        data_structure_confidence = sum(data_structure_indicators) * 0.15
        if data_structure_confidence >= 0.3:
            return {
                "intent": "Data Structure",
                "confidence": min(0.85, data_structure_confidence),
                "document_type": "Data Structure"
            }
            
        # Check for specific types
        if "purchase_order" in json_data or "order_id" in json_data:
            return {
                "intent": "Order Processing",
                "confidence": 0.8,
                "document_type": "Order"
            }
        elif "complaint" in json_data or "ticket_id" in json_data:
            return {
                "intent": "Customer Service",
                "confidence": 0.8,
                "document_type": "Complaint"
            }
        elif "transaction_id" in json_data:
            return {
                "intent": "Financial Processing",
                "confidence": 0.8,
                "document_type": "Transaction"
            }
        
        # Default to generic with slightly increased confidence
        return {
            "intent": "Data Exchange",
            "confidence": 0.4,
            "document_type": "Generic JSON"
        }
    
    def _infer_from_raw_content(self, raw_content, filename):
        """
        Try to infer document intent from raw text content when JSON is invalid.
        """
        # Strip out comments if any
        content = re.sub(r'//.*?(\n|$)|/\*.*?\*/', '', raw_content, flags=re.DOTALL)
        
        # Convert to lowercase for easier matching
        lower_content = content.lower()
        
        # Count occurrences of key indicators
        config_indicators = sum([
            1 if "environment" in lower_content else 0,
            1 if "config" in lower_content or "configuration" in lower_content else 0,
            1 if "settings" in lower_content else 0,
            1 if "database" in lower_content else 0,
            1 if "host" in lower_content and "port" in lower_content else 0,
            1 if "features" in lower_content else 0,
            1 if "api" in lower_content and "key" in lower_content else 0,
            1 if "development" in lower_content or "production" in lower_content or "staging" in lower_content else 0,
            1 if "config" in filename.lower() else 0,
            1 if "settings" in filename.lower() else 0
        ])
        
        schema_indicators = sum([
            1 if "$schema" in content else 0,
            1 if "properties" in lower_content and "{" in content else 0,
            1 if "required" in lower_content and "[" in content else 0,
            1 if "type" in lower_content and "object" in lower_content else 0,
            1 if "definitions" in lower_content else 0,
            1 if "schema" in filename.lower() else 0
        ])
        
        data_indicators = sum([
            1 if "items" in lower_content and "[" in content else 0,
            1 if "data" in lower_content else 0,
            1 if "records" in lower_content else 0,
            1 if "results" in lower_content else 0,
            1 if "list" in lower_content and "[" in content else 0,
            1 if "data" in filename.lower() else 0
        ])
        
        # Determine the most likely type
        if config_indicators >= 3:
            return {
                "intent": "Configuration",
                "confidence": min(0.7, 0.2 + config_indicators * 0.1),
                "document_type": "Configuration"
            }
        elif schema_indicators >= 2:
            return {
                "intent": "Schema Definition",
                "confidence": min(0.7, 0.2 + schema_indicators * 0.1),
                "document_type": "Schema Definition"
            }
        elif data_indicators >= 2:
            return {
                "intent": "Data Structure",
                "confidence": min(0.7, 0.2 + data_indicators * 0.1),
                "document_type": "Data Structure"
            }
        
        # If we can't determine a more specific type, use the filename
        if "error" in filename.lower() or "error" in lower_content:
            return {
                "intent": "Error Report",
                "confidence": 0.3,
                "document_type": "Error Report"
            }
        
        return {
            "intent": "Unknown JSON",
            "confidence": 0.2,
            "document_type": "Generic JSON"
        }
    
    def _count_fields(self, json_data):
        """Count the total number of fields in the JSON."""
        count = 0
        
        def count_fields_recursive(obj):
            nonlocal count
            if isinstance(obj, dict):
                count += len(obj)
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        count_fields_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        count_fields_recursive(item)
        
        count_fields_recursive(json_data)
        return count
    
    def _determine_complexity(self, json_data):
        """Determine the complexity of the JSON structure."""
        # Count nesting levels and total nodes
        max_depth = 0
        total_nodes = 0
        
        def analyze_depth(obj, depth=0):
            nonlocal max_depth, total_nodes
            max_depth = max(depth, max_depth)
            total_nodes += 1
            
            if isinstance(obj, dict):
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        analyze_depth(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        analyze_depth(item, depth + 1)
        
        analyze_depth(json_data)
        
        # Determine complexity based on depth and size
        if max_depth <= 2 and total_nodes < 20:
            return "Simple"
        elif max_depth <= 4 and total_nodes < 50:
            return "Medium"
        else:
            return "Complex"
    
    def _detect_anomalies(self, json_data):
        """Detect anomalies in the JSON data."""
        anomalies = []
        
        if not isinstance(json_data, (dict, list)):
            return anomalies
        
        def check_anomalies(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check null values
                    if value is None:
                        anomalies.append(f"Missing value for field '{current_path}'")
                    
                    # Check numeric fields with non-numeric values
                    if key in ["price", "amount", "total", "unit_price"] and not isinstance(value, (int, float)):
                        anomalies.append(f"Field '{current_path}' should be numeric but is {type(value).__name__}")
                    
                    # Recurse into nested objects
                    if isinstance(value, (dict, list)):
                        check_anomalies(value, current_path)
            
            elif isinstance(obj, list):
                # Check array items
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        check_anomalies(item, f"{path}[{i}]")
        
        # Start the recursive check
        check_anomalies(json_data)
        return anomalies