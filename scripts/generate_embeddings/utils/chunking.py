#!/usr/bin/env python3
"""
Text chunking utility.
"""

import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def chunk_text(
    text: str, chunk_size: int = 1024, chunk_overlap: int = 100
) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    chunks = splitter.split_text(text)
    logger.debug(f"Split text into {len(chunks)} chunks")
    return chunks


if __name__ == "__main__":
    # Test the chunking
    test_text = "Hello world! " * 200  # Create a long string

    chunks = chunk_text(test_text, chunk_size=100, chunk_overlap=20)
    print(f"Created {len(chunks)} chunks")
    print(f"First chunk length: {len(chunks[0])}")
    print(f"Last chunk length: {len(chunks[-1])}")
