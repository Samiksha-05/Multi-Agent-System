import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import os
from .memory_store import MemoryStore

class SQLiteStore(MemoryStore):
    """SQLite implementation of the memory store"""
    
    def __init__(self, db_path: str = "memory.db"):
        """
        Initialize the SQLite memory store
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Documents table stores basic document info and status
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            status TEXT,
            last_updated TEXT
        )
        ''')
        
        # Data table stores all types of data with JSON serialization
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT,
            data_type TEXT,
            data TEXT,
            timestamp TEXT,
            FOREIGN KEY (document_id) REFERENCES documents(document_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def store(self, document_id: str, data_type: str, data: Dict) -> None:
        """Store data in the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ensure document exists
        cursor.execute(
            "INSERT OR IGNORE INTO documents (document_id, status, last_updated) VALUES (?, ?, ?)",
            (document_id, "received", datetime.utcnow().isoformat())
        )
        
        # Store the data
        cursor.execute(
            "INSERT INTO document_data (document_id, data_type, data, timestamp) VALUES (?, ?, ?, ?)",
            (document_id, data_type, json.dumps(data), datetime.utcnow().isoformat())
        )
        
        conn.commit()
        conn.close()
    
    def get(self, document_id: str, data_type: Optional[str] = None) -> Union[Dict, List, None]:
        """Retrieve data from the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if data_type:
            # Get specific data type
            cursor.execute(
                "SELECT data FROM document_data WHERE document_id = ? AND data_type = ? ORDER BY timestamp DESC LIMIT 1",
                (document_id, data_type)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row['data'])
            return None
        else:
            # Get all data for this document
            result = {
                'document_id': document_id,
                'data': {}
            }
            
            # Get document status
            cursor.execute("SELECT status FROM documents WHERE document_id = ?", (document_id,))
            status_row = cursor.fetchone()
            if status_row:
                result['status'] = status_row['status']
            
            # Get all data types
            cursor.execute(
                """
                SELECT data_type, data FROM document_data 
                WHERE document_id = ? 
                GROUP BY data_type 
                HAVING timestamp = MAX(timestamp)
                """,
                (document_id,)
            )
            
            for row in cursor.fetchall():
                result['data'][row['data_type']] = json.loads(row['data'])
            
            conn.close()
            return result
    
    def update_status(self, document_id: str, status: str) -> None:
        """Update the processing status of a document"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE documents SET status = ?, last_updated = ? WHERE document_id = ?",
            (status, datetime.utcnow().isoformat(), document_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_all_documents(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Retrieve a list of all documents in the store"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT document_id, status, last_updated FROM documents ORDER BY last_updated DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        
        result = []
        for row in cursor.fetchall():
            document = dict(row)
            
            # Get document metadata if available
            cursor.execute(
                "SELECT data FROM document_data WHERE document_id = ? AND data_type = 'metadata' ORDER BY timestamp DESC LIMIT 1",
                (row['document_id'],)
            )
            metadata_row = cursor.fetchone()
            
            if metadata_row:
                document['metadata'] = json.loads(metadata_row['data'])
            
            result.append(document)
        
        conn.close()
        return result