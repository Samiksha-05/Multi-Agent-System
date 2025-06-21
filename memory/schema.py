from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

class DocumentMetadata(BaseModel):
    """Schema for document metadata"""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content_type: str
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    size: int
    user: Optional[str] = None

class ClassificationResult(BaseModel):
    """Schema for classification results"""
    document_id: str
    format: str
    intent: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ExtractionResult(BaseModel):
    """Schema for data extraction results"""
    document_id: str
    agent_type: str
    extracted_fields: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ActionRecord(BaseModel):
    """Schema for action records"""
    document_id: str
    action_type: str
    status: str
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ProcessingTrace(BaseModel):
    """Schema for full processing trace"""
    document_id: str
    metadata: DocumentMetadata
    classification: Optional[ClassificationResult] = None
    extractions: Dict[str, ExtractionResult] = {}
    actions: List[ActionRecord] = []
    status: str = "received"
    last_updated: datetime = Field(default_factory=datetime.utcnow)