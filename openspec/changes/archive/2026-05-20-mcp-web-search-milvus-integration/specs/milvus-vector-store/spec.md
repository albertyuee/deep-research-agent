## ADDED Requirements

### Requirement: Zilliz Cloud connection via URI and token
The system SHALL support connecting to Zilliz Cloud (managed Milvus) using a URI endpoint and API token, configured through environment variables `MILVUS_URI` and `MILVUS_TOKEN`.

#### Scenario: Connect to Zilliz Cloud with valid credentials
- **WHEN** `RETRIEVAL_VECTOR_BACKEND=milvus` and `MILVUS_URI` and `MILVUS_TOKEN` are configured
- **THEN** the system creates a MilvusVectorStore that connects to the Zilliz Cloud endpoint and retrieves document count

#### Scenario: Invalid token returns connection error
- **WHEN** the Zilliz Cloud token is invalid
- **THEN** the connection test returns a clear error message about authentication failure

### Requirement: Self-hosted Milvus via host and port
The system SHALL support connecting to a self-hosted Milvus instance using `MILVUS_HOST` and `MILVUS_PORT` when `MILVUS_URI` is not configured.

#### Scenario: Connect to self-hosted Milvus
- **WHEN** `RETRIEVAL_VECTOR_BACKEND=milvus`, `MILVUS_URI` is empty, and `MILVUS_HOST`/`MILVUS_PORT` are set
- **THEN** the system connects to `http://{MILVUS_HOST}:{MILVUS_PORT}`

### Requirement: Automatic embedding dimension detection
The MilvusVectorStore SHALL automatically detect the embedding dimension from the configured embedding service when creating a collection, instead of using a hardcoded value.

#### Scenario: Collection created with correct dimension
- **WHEN** MilvusVectorStore creates a new collection for BAAI/bge-large-zh-v1.5 (1024-dim)
- **THEN** the collection is created with dimension 1024 matching the actual embedding output

### Requirement: Auto-generated primary keys with chunk_id storage
The MilvusVectorStore SHALL let Milvus auto-generate int64 primary keys and store the original chunk_id as a separate varchar field.

#### Scenario: Documents indexed with auto-generated IDs
- **WHEN** documents are inserted into Milvus with string chunk_ids
- **THEN** Milvus auto-generates int64 primary keys and stores chunk_ids in a `chunk_id` field for retrieval

### Requirement: Vector store backend switchable via settings
The system SHALL select between ChromaDB and Milvus backends based on `RETRIEVAL_VECTOR_BACKEND` setting, using a factory function `create_vector_store()`.

#### Scenario: Switch to Milvus via API
- **WHEN** `PATCH /api/v1/settings` sets `retrieval.vector_backend` to "milvus"
- **THEN** the setting is written to `.env` and `reload_settings()` applies it; a restart is needed for agents to pick up the new backend

### Requirement: Settings page shows Milvus configuration fields
The settings page SHALL display Zilliz Cloud URI and Token fields when Milvus is selected as the vector store backend, and self-hosted Host/Port fields for local deployments.

#### Scenario: Select Milvus in settings
- **WHEN** user selects "Milvus 远程" radio button
- **THEN** the page reveals Zilliz Cloud URI/Token fields in a purple-bordered card and self-hosted Host/Port fields in a gray card
