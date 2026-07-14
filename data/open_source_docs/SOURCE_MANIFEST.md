# 开放许可测试语料清单

生成日期：2026-07-14

这套语料用于测试快速检索、深度研究和多跳推理。上游内容的权利与许可证归各项目所有。

## 文件与许可证

| 文件 | 项目 | 许可证 | 上游来源 |
|---|---|---|---|
| `microsoft_graphrag.md` | Microsoft GraphRAG | [MIT](https://github.com/microsoft/graphrag/blob/main/LICENSE) | [GitHub](https://github.com/microsoft/graphrag) |
| `langchain_langgraph.md` | LangGraph | [MIT](https://github.com/langchain-ai/langgraph/blob/main/LICENSE) | [GitHub](https://github.com/langchain-ai/langgraph) |
| `deepset_haystack.md` | Haystack | [Apache-2.0](https://github.com/deepset-ai/haystack/blob/main/LICENSE) | [GitHub](https://github.com/deepset-ai/haystack) |
| `llamaindex.md` | LlamaIndex | [MIT](https://github.com/run-llama/llama_index/blob/main/LICENSE) | [GitHub](https://github.com/run-llama/llama_index) |
| `chroma.md` | Chroma | [Apache-2.0](https://github.com/chroma-core/chroma/blob/main/LICENSE) | [GitHub](https://github.com/chroma-core/chroma) |
| `qdrant.md` | Qdrant | [Apache-2.0](https://github.com/qdrant/qdrant/blob/master/LICENSE) | [GitHub](https://github.com/qdrant/qdrant) |
| `hotpotqa.md` | HotpotQA | [CC BY-SA 4.0 (dataset) / Apache-2.0 (code)](https://github.com/hotpotqa/hotpot#license) | [GitHub](https://github.com/hotpotqa/hotpot) |

## 建议测试问题

- GraphRAG 与传统向量 RAG 的处理方式有什么区别？
- LangGraph 如何支持有状态、可恢复的 Agent 工作流？
- Haystack 的 Pipeline 与 Agent 能力分别适合什么场景？
- LlamaIndex 在私有数据与大模型之间承担什么角色？
- Chroma 为 AI 应用提供了哪些检索和向量存储能力？
- Qdrant 的过滤、混合查询和分布式能力适合哪些 RAG 场景？
- HotpotQA 如何通过 supporting facts 评估多跳问答？
- GraphRAG、LangGraph、Haystack 和 LlamaIndex 在一套深度研究系统中可以分别承担什么职责？
- 如果要构建支持过滤和多跳推理的 RAG，Qdrant、Chroma 与 HotpotQA 分别能提供什么？

## 说明

- 文档内容可能随上游仓库更新；本清单记录了本次下载日期。
- 测试时可以先关闭联网搜索，以确认回答确实来自本地知识库。
- 引用或再分发时请遵守每个项目对应的许可证要求。
