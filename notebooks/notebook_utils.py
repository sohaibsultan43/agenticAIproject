"""
Utility functions for Jupyter notebooks in ScholarSync.

This module provides helper functions to convert between different
document formats used by LlamaIndex and LangChain.
"""

from typing import List
from llama_index.core import Document as LlamaDocument
from langchain_core.documents import Document as LangChainDocument


def llama_to_langchain_docs(llama_docs: List[LlamaDocument]) -> List[LangChainDocument]:
    """
    Convert LlamaIndex Document objects to LangChain Document objects.
    
    LlamaIndex Documents have:
        - text: The document content
        - metadata: Dict of metadata
    
    LangChain Documents have:
        - page_content: The document content
        - metadata: Dict of metadata
    
    Args:
        llama_docs: List of LlamaIndex Document objects
        
    Returns:
        List of LangChain Document objects
    """
    langchain_docs = []
    
    for llama_doc in llama_docs:
        langchain_doc = LangChainDocument(
            page_content=llama_doc.text,
            metadata=llama_doc.metadata
        )
        langchain_docs.append(langchain_doc)
    
    return langchain_docs


def langchain_to_llama_docs(langchain_docs: List[LangChainDocument]) -> List[LlamaDocument]:
    """
    Convert LangChain Document objects to LlamaIndex Document objects.
    
    Args:
        langchain_docs: List of LangChain Document objects
        
    Returns:
        List of LlamaIndex Document objects
    """
    llama_docs = []
    
    for lc_doc in langchain_docs:
        llama_doc = LlamaDocument(
            text=lc_doc.page_content,
            metadata=lc_doc.metadata
        )
        llama_docs.append(llama_doc)
    
    return llama_docs
