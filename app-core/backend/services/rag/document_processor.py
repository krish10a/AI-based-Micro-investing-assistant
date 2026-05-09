"""Document processing and text chunking for RAG."""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True)
class DocumentChunk:
    """A chunk of text with metadata for RAG retrieval."""

    content: str
    chunk_id: str
    source: str  # File path or URL
    chunk_index: int
    total_chunks: int
    metadata: dict[str, str] | None = None


class DocumentProcessor:
    """Handles document loading and text chunking for RAG systems.

    This processor is designed to be:
    - Modular: Easy to extend with new document types
    - Production-ready: Handles edge cases and errors gracefully
    - Multi-agent ready: Stateless and reusable
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """Initialize the document processor.

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between consecutive chunks
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_text(self, text: str, source: str = "unknown") -> list[DocumentChunk]:
        """Process raw text into chunks.

        Args:
            text: The text to chunk
            source: Source identifier (file path, URL, etc.)

        Returns:
            List of DocumentChunk objects
        """
        if not text or not text.strip():
            return []

        # Clean and normalize text
        text = self._clean_text(text)

        # Split into chunks
        chunks = self._create_chunks(text)

        # Create DocumentChunk objects
        result = []
        for i, chunk_content in enumerate(chunks):
            result.append(
                DocumentChunk(
                    content=chunk_content,
                    chunk_id=f"{self._safe_filename(source)}_{i}",
                    source=source,
                    chunk_index=i,
                    total_chunks=len(chunks),
                    metadata={"char_length": str(len(chunk_content))},
                )
            )

        return result

    def process_file(self, file_path: str | Path) -> list[DocumentChunk]:
        """Load and chunk a file.

        Args:
            file_path: Path to the file

        Returns:
            List of DocumentChunk objects

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is not supported
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()

        if suffix == ".txt":
            text = self._read_text_file(file_path)
        elif suffix == ".md":
            text = self._read_text_file(file_path)
        elif suffix == ".json":
            text = self._read_json_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        return self.process_text(text, source=str(file_path))

    def process_multiple_files(
        self, file_paths: list[str | Path]
    ) -> Iterator[list[DocumentChunk]]:
        """Process multiple files, yielding chunks for each file.

        Args:
            file_paths: List of file paths to process

        Yields:
            List of DocumentChunk objects for each file
        """
        for file_path in file_paths:
            try:
                chunks = self.process_file(file_path)
                yield chunks
            except Exception as e:
                # Log error but continue processing other files
                print(f"Error processing {file_path}: {e}")
                continue

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove excessive newlines (keep max 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Trim leading/trailing whitespace
        text = text.strip()

        return text

    def _create_chunks(self, text: str) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text] if text else []

        chunks = []
        start = 0

        while start < len(text):
            # End of current chunk
            end = start + self.chunk_size

            # If not the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence boundary within overlap region
                overlap_region = text[end - self.chunk_overlap : end]
                break_points = [
                    i
                    for i, char in enumerate(overlap_region)
                    if char in ".!?"
                ]

                if break_points:
                    # Break at the last sentence boundary
                    last_break = max(break_points)
                    end = end - self.chunk_overlap + last_break + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position
            start = end - self.chunk_overlap

            # Prevent infinite loop
            if start <= 0 and chunks:
                break

        return chunks

    def _safe_filename(self, path: str) -> str:
        """Create a safe filename from a path.

        Args:
            path: File path or URL

        Returns:
            Sanitized filename
        """
        # Get just the filename
        name = Path(path).name if Path(path).exists() else path

        # Replace invalid characters
        name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)

        # Limit length
        if len(name) > 50:
            name = name[:50]

        return name

    def _read_text_file(self, file_path: Path) -> str:
        """Read a text file.

        Args:
            file_path: Path to file

        Returns:
            File contents as string
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_json_file(self, file_path: Path) -> str:
        """Read a JSON file and convert to text.

        Args:
            file_path: Path to JSON file

        Returns:
            Text representation of JSON content
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert JSON to readable text
        return self._json_to_text(data)

    def _json_to_text(self, data: dict | list, indent: int = 0) -> str:
        """Convert JSON data to readable text.

        Args:
            data: JSON data
            indent: Current indentation level

        Returns:
            Text representation
        """
        lines = []
        prefix = " " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._json_to_text(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}[{i}]:")
                    lines.append(self._json_to_text(item, indent + 1))
                else:
                    lines.append(f"{prefix}[{i}]: {item}")

        return "\n".join(lines)
