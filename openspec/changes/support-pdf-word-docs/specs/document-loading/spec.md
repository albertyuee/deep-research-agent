## ADDED Requirements

### Requirement: Document Loader supports multiple formats
The system SHALL provide a `DocumentLoader` class that supports loading and parsing `.pdf`, `.docx`, `.md`, and `.txt` files, automatically detecting the format by file extension.

#### Scenario: Load PDF file
- **WHEN** a PDF file path is passed to `DocumentLoader.load_file()`
- **THEN** the system returns a list of text chunks extracted from all pages, each with metadata including `source_path`, `file_name`, and `file_type`

#### Scenario: Load DOCX file
- **WHEN** a `.docx` file path is passed to `DocumentLoader.load_file()`
- **THEN** the system returns a list of text chunks extracted from all paragraphs, each with metadata including `source_path`, `file_name`, and `file_type`

#### Scenario: Load Markdown or plain text file
- **WHEN** a `.md` or `.txt` file path is passed to `DocumentLoader.load_file()`
- **THEN** the system reads the file as UTF-8 text and returns chunks split by double-newline

#### Scenario: Unsupported file format
- **WHEN** a file with an unsupported extension (e.g., `.ppt`, `.xls`) is passed to `DocumentLoader.load_file()`
- **THEN** the system raises a clear `ValueError` with a message listing supported formats

### Requirement: Batch directory loading
The system SHALL provide a method to recursively scan a directory and load all supported documents.

#### Scenario: Recursive directory scan
- **WHEN** `DocumentLoader.load_directory()` is called with a directory path
- **THEN** the system recursively finds all `.pdf`, `.docx`, `.md`, `.txt` files, returns chunks from all files, each with metadata including the relative source path

#### Scenario: Empty or non-existent directory
- **WHEN** the specified directory does not exist or contains no supported files
- **THEN** the system returns an empty list without raising an error

### Requirement: Chunk filtering
The system SHALL filter out chunks shorter than a configurable minimum length (default 50 characters).

#### Scenario: Short chunk filtered out
- **WHEN** a document paragraph has fewer than 50 characters after stripping whitespace
- **THEN** that paragraph is excluded from the returned chunks

### Requirement: One-click indexing script
The system SHALL provide a script at `scripts/index_documents.py` that accepts a directory path as a command-line argument, loads all documents, chunks them, and indexes them into both the vector store (Chroma) and BM25 retriever.

#### Scenario: Index a directory of documents
- **WHEN** the user runs `python scripts/index_documents.py /path/to/docs`
- **THEN** all supported files in the directory are parsed, chunked, and indexed into both Chroma vector store and BM25, with progress printed to stdout

#### Scenario: No documents found
- **WHEN** the user runs the script on a directory with no supported files
- **THEN** the script prints a warning and exits with code 0

#### Scenario: Script accepts optional arguments
- **WHEN** the user runs the script with `--min-chunk-length 100` or `--exclude "*.pdf"`
- **THEN** the script uses those parameters for chunk filtering and file exclusion
