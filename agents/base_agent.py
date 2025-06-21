# File: agents/base_agent.py

import logging
from abc import ABC, abstractmethod

class Agent(ABC):
    """Base abstract class for specialized agents."""
    
    def __init__(self, memory_store):
        """
        Initialize the agent with a memory store.
        
        Args:
            memory_store: A reference to the shared memory store
        """
        self.memory_store = memory_store
    
    @abstractmethod
    def process(self, file_path, metadata):
        """
        Process a document file and extract relevant information.
        
        Args:
            file_path (str): Path to the file to process
            metadata (dict): Metadata about the file
        
        Returns:
            dict: The results of processing
        """
        pass