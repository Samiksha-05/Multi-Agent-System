# File: memory/memory_store.py

import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

class MemoryStore:
    """
    Simple in-memory storage for document processing results.
    In a production system, this would be replaced with a database.
    """
    
    def __init__(self):
        self.documents = {}
    
    def store(self, document_id: str, data_type: str, data: Dict) -> None:
        """
        Store data for a document.
        
        Args:
            document_id: Unique identifier for the document
            data_type: Type of data being stored (e.g., "metadata", "classification")
            data: The data to store
        """
        if document_id not in self.documents:
            self.documents[document_id] = {
                "document_id": document_id,
                "status": "received",
                "data": {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        
        # Update document data
        self.documents[document_id]["data"][data_type] = data
        self.documents[document_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def update_status(self, document_id: str, status: str) -> None:
        """
        Update the status of a document.
        
        Args:
            document_id: Unique identifier for the document
            status: New status value
        """
        if document_id in self.documents:
            self.documents[document_id]["status"] = status
            self.documents[document_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def get(self, document_id: str) -> Dict:
        """
        Get all data for a document.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            Dictionary containing all document data, or None if not found
        """
        return self.documents.get(document_id)
    
    def get_all_documents(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Get a list of all documents.
        
        Args:
            limit: Maximum number of documents to return
            offset: Starting position in the document list
            
        Returns:
            List of document dictionaries
        """
        # Sort by updated_at in descending order
        sorted_ids = sorted(
            self.documents.keys(), 
            key=lambda id: self.documents[id].get("updated_at", ""), 
            reverse=True
        )
        
        # Apply pagination
        paginated_ids = sorted_ids[offset:offset+limit]
        
        return [self.documents[id] for id in paginated_ids]
    
    def get_all(self, limit=10, offset=0):
        """
        Alias for get_all_documents to maintain API compatibility.
        
        Args:
            limit: Maximum number of documents to return
            offset: Starting position in the document list
                
        Returns:
            List of document dictionaries
        """
        return self.get_all_documents(limit=limit, offset=offset)