## ADDED Requirements

### Requirement: Test LLM connection from settings page
The system SHALL provide a "测试连接" button in the LLM configuration section that sends a minimal chat request and displays success or failure with a preview of the response.

#### Scenario: Successful LLM connection test
- **WHEN** user clicks "测试连接" in the LLM section with valid API credentials
- **THEN** the system displays a success alert with "LLM 连接成功" and a preview of the response text

#### Scenario: Failed LLM connection test
- **WHEN** user clicks "测试连接" with invalid or missing API credentials
- **THEN** the system displays an error alert with the specific failure reason

### Requirement: Test Embedding connection from settings page
The system SHALL provide a "测试连接" button in the Embedding configuration section that embeds a test string and displays the resulting vector dimension.

#### Scenario: Successful Embedding connection test
- **WHEN** user clicks "测试连接" in the Embedding section with valid configuration
- **THEN** the system displays "嵌入模型连接成功，维度: N" where N is the actual vector dimension

#### Scenario: Failed Embedding connection test
- **WHEN** the embedding service is unreachable or misconfigured
- **THEN** the system displays an error alert with the failure reason

### Requirement: Test vector store connection from settings page
The system SHALL provide a "测试连接" button in the Vector Store configuration section that connects to the configured backend and reports document count.

#### Scenario: Successful Milvus connection test
- **WHEN** user clicks "测试连接" with Zilliz Cloud configured and valid credentials
- **THEN** the system displays "Zilliz Cloud 连接成功，已索引 N 个文档" with the actual count

#### Scenario: Successful ChromaDB connection test
- **WHEN** user clicks "测试连接" with ChromaDB configured
- **THEN** the system displays the local ChromaDB document count

### Requirement: Connection test shows loading state
Each test button SHALL show a loading spinner while the test is in progress and disable further clicks.

#### Scenario: Test in progress
- **WHEN** user clicks "测试连接" and the request is pending
- **THEN** the button shows "测试中..." with a loading spinner and is disabled

### Requirement: Masked tokens are not saved to configuration
The settings save logic SHALL skip fields containing "***" (masked values) for both `api_key` and `token` fields to prevent overwriting real credentials with display-safe placeholders.

#### Scenario: Save with masked token
- **WHEN** the frontend sends a masked token value containing "***" in a token field
- **THEN** the backend skips that field and preserves the existing value in `.env`
