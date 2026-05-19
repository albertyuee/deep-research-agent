## ADDED Requirements

### Requirement: Agent autonomously decides when to search the web
The agent's decomposition node SHALL mark each sub-query with a `data_source` field (local, web, or both) based on whether the information is likely available in the local knowledge base or requires real-time data.

#### Scenario: Query about real-time events triggers web search
- **WHEN** user asks about recent events or time-sensitive information with web search enabled
- **THEN** the decomposer marks at least one sub-query with `data_source: "web"` or `data_source: "both"`

#### Scenario: Query about indexed knowledge stays local
- **WHEN** user asks a question answerable from indexed documents
- **THEN** the decomposer marks all sub-queries with `data_source: "local"`

### Requirement: Web search results merge with local retrieval results
The retrieval node SHALL execute web search when `data_source` is "web" or "both", convert results to the same format as local retrieval results, and merge them with local results appearing first.

#### Scenario: Both local and web sources used
- **WHEN** a sub-query has `data_source: "both"` and web search is available
- **THEN** the agent executes both local retrieval and web search, merges results into a unified list, and emits `retrieval_combined` with local and web counts

#### Scenario: Web-only data source skips local retrieval
- **WHEN** a sub-query has `data_source: "web"` and web search is available
- **THEN** the agent skips local retrieval, executes only web search, and emits `web_search_start` followed by `web_search_result` with structured result items

### Requirement: Web search toggle controls availability
The frontend SHALL provide a switch on the research page that controls whether web search is available. The backend SHALL check both the user toggle (`enable_web_search`) AND the configured API key before enabling web search.

#### Scenario: Toggle off disables web search
- **WHEN** user submits a research query with `enable_web_search: false`
- **THEN** the decomposer only suggests `data_source: "local"` regardless of API key configuration

#### Scenario: Toggle on but no API key disables web search
- **WHEN** user submits with `enable_web_search: true` but no Tavily API key is configured
- **THEN** the decomposer only suggests `data_source: "local"` and no web search occurs

### Requirement: ChromaDB failure falls back to web results
When `data_source` is "both" and local ChromaDB retrieval fails, the agent SHALL catch the exception and continue with web-only results instead of crashing.

#### Scenario: ChromaDB connection reset during retrieval
- **WHEN** ChromaDB embedded server returns "Connection reset by peer" and data_source is "both"
- **THEN** the retrieval node emits a local retrieval result with 0 results and an error field, then proceeds with web search

#### Scenario: ChromaDB failure with local-only data source
- **WHEN** ChromaDB fails and data_source is "local" only
- **THEN** the exception is re-raised to trigger the existing retry mechanism
