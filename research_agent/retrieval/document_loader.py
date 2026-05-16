from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple


class LoadedChunk(NamedTuple):
    chunk_id: str
    content: str
    metadata: dict


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


class DocumentLoader:
    """Load and chunk documents from various file formats.

    Supports: PDF (.pdf), Word (.docx), Markdown (.md), plain text (.txt).
    """

    def __init__(self, min_chunk_length: int = 50, max_chunk_chars: int = 300):
        self.min_chunk_length = min_chunk_length
        self.max_chunk_chars = max_chunk_chars

    def load_file(self, file_path: str | Path) -> list[LoadedChunk]:
        """Load a single file and return chunked text.

        Args:
            file_path: Path to the document file.

        Returns:
            List of LoadedChunk with content and metadata.

        Raises:
            ValueError: If the file format is not supported.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: '{ext}'. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        if ext == ".pdf":
            raw_text = self._load_pdf(file_path)
        elif ext == ".docx":
            raw_text = self._load_docx(file_path)
        else:
            raw_text = self._load_text(file_path)

        return self._chunk_text(
            raw_text,
            source_path=str(file_path),
            file_name=file_path.name,
            file_type=ext.lstrip("."),
        )

    def load_directory(
        self,
        directory: str | Path,
        exclude: str | None = None,
    ) -> list[LoadedChunk]:
        """Recursively scan a directory and load all supported documents.

        Args:
            directory: Path to the directory to scan.
            exclude: Optional glob pattern for files to exclude (e.g. "*.pdf").

        Returns:
            List of LoadedChunk from all discovered documents.
        """
        from fnmatch import fnmatch

        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            return []

        all_chunks: list[LoadedChunk] = []
        found_files = False

        for root, _dirs, files in os.walk(directory):
            for fname in sorted(files):
                file_path = Path(root) / fname
                ext = file_path.suffix.lower()

                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                if exclude and fnmatch(fname, exclude):
                    continue

                found_files = True
                try:
                    chunks = self.load_file(file_path)
                    # Update metadata with relative path
                    for chunk in chunks:
                        chunk.metadata["source_path"] = str(file_path)
                    all_chunks.extend(chunks)
                except Exception:
                    # Skip files that fail to parse
                    continue

        if not found_files:
            return []

        return all_chunks

    # ── Private parsers ──────────────────────────────────────────

    def _load_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF file using PyMuPDF."""
        import fitz  # PyMuPDF

        doc = fitz.open(str(file_path))
        pages: list[str] = []
        try:
            for page in doc:
                text = page.get_text()
                if text.strip():
                    pages.append(text.strip())
        finally:
            doc.close()

        return "\n\n".join(pages)

    def _load_docx(self, file_path: Path) -> str:
        """Extract text from a Word (.docx) file using python-docx."""
        from docx import Document

        doc = Document(str(file_path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _load_text(self, file_path: Path) -> str:
        """Read plain text from .md or .txt files."""
        return file_path.read_text(encoding="utf-8")

    def _split_long_text(self, text: str) -> list[str]:
        """Split a long text into smaller chunks respecting max_chunk_chars.

        Tries to split at sentence boundaries (。！？\\n) first,
        then falls back to fixed-width windows.
        """
        if len(text) <= self.max_chunk_chars:
            return [text]

        # Try splitting at Chinese/English sentence boundaries
        import re
        sentences = re.split(r'(?<=[。！？.!?\n])\s*', text)
        chunks: list[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) <= self.max_chunk_chars:
                current += sent
            else:
                if current.strip():
                    chunks.append(current.strip())
                # If a single sentence exceeds the limit, split by fixed window
                if len(sent) > self.max_chunk_chars:
                    for j in range(0, len(sent), self.max_chunk_chars):
                        piece = sent[j:j + self.max_chunk_chars]
                        if piece.strip():
                            chunks.append(piece.strip())
                    current = ""
                else:
                    current = sent
        if current.strip():
            chunks.append(current.strip())

        return chunks or [text[:self.max_chunk_chars]]

    def _chunk_text(
        self,
        text: str,
        source_path: str = "",
        file_name: str = "",
        file_type: str = "",
    ) -> list[LoadedChunk]:
        """Split text into chunks by double-newline, filtering short chunks.
        Long paragraphs are further split to avoid embedding API limits.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[LoadedChunk] = []
        chunk_idx = 0

        for para in paragraphs:
            sub_chunks = self._split_long_text(para)
            for sub in sub_chunks:
                if len(sub) < self.min_chunk_length:
                    continue
                chunk_id = f"{Path(source_path).stem}_chunk_{chunk_idx}" if source_path else f"chunk_{chunk_idx}"
                chunks.append(
                    LoadedChunk(
                        chunk_id=chunk_id,
                        content=sub,
                        metadata={
                            "source_path": source_path,
                            "file_name": file_name,
                            "file_type": file_type,
                            "chunk_index": chunk_idx,
                        },
                    )
                )
                chunk_idx += 1

        return chunks
