# File: memory/__init__.py

# Import the MemoryStore class directly
from memory.memory_store import MemoryStore

# Define the get_memory_store function that was being imported
def get_memory_store():
    """Returns a new instance of MemoryStore"""
    return MemoryStore()