## ADDED Requirements

### Requirement: SiliconFlow as default LLM provider
The system SHALL default to SiliconFlow as the LLM provider with model `Qwen/Qwen3-8B` and base URL `https://api.siliconflow.cn/v1`.

#### Scenario: Default provider configuration
- **WHEN** user runs the project without modifying .env
- **THEN** system uses SiliconFlow API with Qwen/Qwen3-8B model

### Requirement: SiliconFlow API key configuration
The system SHALL read the SiliconFlow API key from the `LLM_API_KEY` environment variable.

#### Scenario: API key configured
- **WHEN** `LLM_API_KEY` is set to a valid SiliconFlow API key
- **THEN** LLM calls succeed with SiliconFlow backend

#### Scenario: API key missing
- **WHEN** `LLM_API_KEY` is empty or not configured
- **THEN** system raises a clear configuration error at startup

### Requirement: Multi-provider fallback documentation
The README SHALL document how to switch between SiliconFlow, Qwen, and OpenAI providers.

#### Scenario: User wants to switch provider
- **WHEN** user reads README quick start section
- **THEN** they find clear instructions for configuring each supported provider

### Requirement: Project README completeness
The README SHALL include: project overview, architecture diagram, quick start guide, API documentation, interview talking points, and comparison with sql-agent-kit.

#### Scenario: New developer onboarding
- **WHEN** a developer reads README for the first time
- **THEN** they can get the project running within 10 minutes
