<template>
  <div>
    <!-- Header -->
    <div class="sticky top-0 z-10 -mx-2 mb-6 flex items-center justify-between rounded-2xl bg-white/90 px-2 py-3 backdrop-blur">
      <div>
        <h1 class="text-xl font-bold text-gray-800">系统设置</h1>
        <p class="text-sm text-gray-400 mt-0.5">集中配置模型、检索、观测追踪和外部服务</p>
      </div>
      <n-button type="primary" :loading="store.isSaving" @click="onSave" size="large">
        <template #icon><n-icon><save-outline /></n-icon></template>
        保存配置
      </n-button>
    </div>

    <n-spin :show="store.isLoading">
      <!-- Alerts -->
      <n-alert v-if="store.error" type="error" :bordered="false" class="mb-4" closable @close="store.error = null">
        {{ store.error }}
      </n-alert>
      <n-alert v-if="store.successMsg" type="success" :bordered="false" class="mb-4" closable>
        {{ store.successMsg }}
      </n-alert>
      <n-alert v-if="testResult" :type="testResult.ok ? 'success' : 'error'" :bordered="false" class="mb-4" closable @close="testResult = null">
        {{ testResult.msg }}
      </n-alert>

      <div v-if="store.settings" class="space-y-5">
        <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
            <p class="text-xs text-gray-400">LangSmith</p>
            <p class="mt-1 text-lg font-semibold" :class="form.langsmith.tracing ? 'text-emerald-600' : 'text-gray-700'">
              {{ form.langsmith.tracing ? 'Tracing 已开启' : 'Tracing 未开启' }}
            </p>
            <p class="mt-1 truncate text-xs text-gray-400">{{ form.langsmith.project || '未设置项目名' }}</p>
          </div>
          <div class="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
            <p class="text-xs text-gray-400">向量存储</p>
            <p class="mt-1 text-lg font-semibold text-gray-700">{{ form.retrieval.vector_backend === 'milvus' ? 'Milvus' : 'ChromaDB' }}</p>
            <p class="mt-1 text-xs text-gray-400">{{ store.systemInfo?.chunk_count ?? 0 }} chunks</p>
          </div>
          <div class="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
            <p class="text-xs text-gray-400">网络搜索</p>
            <p class="mt-1 text-lg font-semibold" :class="form.mcp.web_search_enabled ? 'text-emerald-600' : 'text-gray-700'">
              {{ form.mcp.web_search_enabled ? '已启用' : '未启用' }}
            </p>
            <p class="mt-1 text-xs text-gray-400">Tavily MCP</p>
          </div>
          <div class="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
            <p class="text-xs text-gray-400">Rerank</p>
            <p class="mt-1 text-lg font-semibold" :class="form.rerank.enabled ? 'text-emerald-600' : 'text-gray-700'">
              {{ form.rerank.enabled ? '已启用' : '未启用' }}
            </p>
            <p class="mt-1 truncate text-xs text-gray-400">{{ form.rerank.model }}</p>
          </div>
        </div>

        <!-- LLM -->
        <SettingsSection title="LLM 大语言模型">
          <template #actions>
            <n-button size="small" :loading="testing.llm" @click="testLLM" ghost>
              <template #icon><n-icon><flash-outline /></n-icon></template>
              {{ testing.llm ? '测试中...' : '测试连接' }}
            </n-button>
          </template>
          <div class="grid grid-cols-2 gap-x-6 gap-y-4">
            <FormField label="提供商">
              <n-select v-model:value="form.llm.provider" :options="llmProviders" size="medium" />
            </FormField>
            <FormField label="模型名称">
              <n-input v-model:value="form.llm.model" size="medium" placeholder="deepseek-ai/DeepSeek-V3" />
            </FormField>
            <FormField label="API Key" class="col-span-2">
              <n-input v-model:value="form.llm.api_key" type="password" show-password-on="click" size="medium" placeholder="留空则不修改" />
            </FormField>
            <FormField label="API 地址（可选）">
              <n-input v-model:value="form.llm.base_url" size="medium" placeholder="默认使用官方地址" />
            </FormField>
            <FormField label="Max Tokens">
              <n-input-number v-model:value="form.llm.max_tokens" size="medium" :min="256" :max="32768" class="w-full" />
            </FormField>
            <FormField :label="`Temperature: ${form.llm.temperature}`" class="col-span-2">
              <n-slider v-model:value="form.llm.temperature" :min="0" :max="2" :step="0.1" />
            </FormField>
          </div>
        </SettingsSection>

        <!-- LangSmith -->
        <SettingsSection title="LangSmith 观测追踪">
          <template #actions>
            <n-button size="small" :loading="testing.langsmith" @click="testLangSmith" ghost>
              <template #icon><n-icon><flash-outline /></n-icon></template>
              {{ testing.langsmith ? '测试中...' : '测试连接' }}
            </n-button>
          </template>
          <div class="grid grid-cols-2 gap-x-6 gap-y-4">
            <FormField label="启用 Tracing" class="col-span-2">
              <n-switch v-model:value="form.langsmith.tracing" />
              <span class="ml-3 text-sm text-gray-400">开启后上传 LangGraph、LLM、Embedding、Rerank 和 Web Search trace</span>
            </FormField>
            <FormField label="项目名称">
              <n-input v-model:value="form.langsmith.project" size="medium" placeholder="deep-research-agent" />
            </FormField>
            <FormField label="API Endpoint">
              <n-input v-model:value="form.langsmith.endpoint" size="medium" placeholder="https://api.smith.langchain.com" />
            </FormField>
            <FormField label="API Key" class="col-span-2">
              <n-input v-model:value="form.langsmith.api_key" type="password" show-password-on="click" size="medium" placeholder="留空则不修改" />
            </FormField>
          </div>
          <n-alert type="info" :bordered="false" class="mt-4 text-xs">
            保存后会同步写入 LANGSMITH_* 和 LANGCHAIN_* 兼容变量；如果开关不生效，请重启后端。
          </n-alert>
        </SettingsSection>

        <!-- Embedding -->
        <SettingsSection title="Embedding 嵌入模型">
          <template #actions>
            <n-button size="small" :loading="testing.embedding" @click="testEmbedding" ghost>
              <template #icon><n-icon><flash-outline /></n-icon></template>
              {{ testing.embedding ? '测试中...' : '测试连接' }}
            </n-button>
          </template>
          <div class="grid grid-cols-2 gap-x-6 gap-y-4">
            <FormField label="运行模式" class="col-span-2">
              <n-radio-group v-model:value="form.embedding.mode">
                <n-radio-button value="api">API 远程</n-radio-button>
                <n-radio-button value="local">本地模型</n-radio-button>
              </n-radio-group>
            </FormField>
            <FormField label="计算设备" v-if="form.embedding.mode === 'local'">
              <n-select v-model:value="form.embedding.device" :options="[{ label: 'CPU', value: 'cpu' }, { label: 'CUDA (GPU)', value: 'cuda' }]" size="medium" />
            </FormField>
            <FormField label="模型名称">
              <n-input v-model:value="form.embedding.model" size="medium" placeholder="BAAI/bge-large-zh-v1.5" />
            </FormField>
            <FormField label="API 地址">
              <n-input v-model:value="form.embedding.api_base_url" size="medium" placeholder="https://api.siliconflow.cn/v1" />
            </FormField>
            <FormField label="API Key" v-if="form.embedding.mode === 'api'" class="col-span-2">
              <n-input v-model:value="form.embedding.api_key" type="password" show-password-on="click" size="medium" placeholder="留空则不修改" />
            </FormField>
            <FormField label="检索查询字符上限" v-if="form.embedding.mode === 'api'">
              <n-input-number v-model:value="form.embedding.query_max_chars" size="medium" :min="100" :max="2000" :step="50" class="w-full" />
            </FormField>
          </div>
        </SettingsSection>

        <!-- Vector Store -->
        <SettingsSection title="Vector Store 向量存储">
          <template #actions>
            <n-button size="small" :loading="testing.milvus" @click="testMilvus" ghost>
              <template #icon><n-icon><flash-outline /></n-icon></template>
              {{ testing.milvus ? '测试中...' : '测试连接' }}
            </n-button>
          </template>
          <FormField label="存储后端" class="mb-4">
            <n-radio-group v-model:value="form.retrieval.vector_backend">
              <n-radio-button value="chroma">ChromaDB 本地</n-radio-button>
              <n-radio-button value="milvus">Milvus 远程</n-radio-button>
            </n-radio-group>
          </FormField>

          <div v-if="form.retrieval.vector_backend === 'milvus'" class="ml-1 pl-4 border-l-2 border-purple-200 space-y-4">
            <div class="bg-purple-50/50 rounded-lg p-4">
              <p class="text-sm font-medium text-purple-800 mb-3">Zilliz Cloud（推荐）</p>
              <div class="space-y-3">
                <FormField label="服务 URI">
                  <n-input v-model:value="form.milvus.uri" size="medium" placeholder="https://in03-xxxx.api.vectordb.zillizcloud.com" />
                </FormField>
                <FormField label="API Token">
                  <n-input v-model:value="form.milvus.token" type="password" show-password-on="click" size="medium" placeholder="留空则不修改" />
                </FormField>
              </div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <p class="text-sm font-medium text-gray-500 mb-3">自建 Milvus（不使用云服务时填写）</p>
              <div class="grid grid-cols-2 gap-3">
                <FormField label="Host">
                  <n-input v-model:value="form.milvus.host" size="medium" placeholder="localhost" />
                </FormField>
                <FormField label="Port">
                  <n-input-number v-model:value="form.milvus.port" size="medium" :min="1" :max="65535" class="w-full" />
                </FormField>
              </div>
              <FormField label="Collection 名称" class="mt-3">
                <n-input v-model:value="form.milvus.collection_name" size="medium" placeholder="research_docs" />
              </FormField>
            </div>
          </div>

          <n-alert type="warning" :bordered="false" class="mt-4 text-xs">
            切换存储后端需重启生效，且需要在新后端重新索引文档。
          </n-alert>
        </SettingsSection>

        <!-- Retrieval -->
        <SettingsSection title="Retrieval 检索参数">
          <div class="grid grid-cols-3 gap-x-6 gap-y-4">
            <FormField label="Top-K 结果数">
              <n-input-number v-model:value="form.retrieval.top_k" size="medium" :min="1" :max="50" class="w-full" />
            </FormField>
            <FormField label="最大重试次数">
              <n-input-number v-model:value="form.retrieval.max_retries" size="medium" :min="0" :max="10" class="w-full" />
            </FormField>
            <FormField :label="`相似度阈值: ${form.retrieval.critique_threshold}`">
              <n-slider v-model:value="form.retrieval.critique_threshold" :min="0.3" :max="0.95" :step="0.05" />
            </FormField>
            <FormField :label="`RRF 融合参数 K: ${form.retrieval.rrf_k}`">
              <n-slider v-model:value="form.retrieval.rrf_k" :min="0" :max="120" :step="1" />
            </FormField>
          </div>
        </SettingsSection>

        <SettingsSection title="Multi-hop 多跳推理">
          <div class="grid grid-cols-3 gap-x-6 gap-y-4">
            <FormField label="启用多跳推理">
              <n-switch v-model:value="form.reasoning.enabled" />
            </FormField>
            <FormField label="最大推理跳数">
              <n-input-number v-model:value="form.reasoning.max_hops" size="medium" :min="1" :max="8" class="w-full" />
            </FormField>
            <FormField label="上下文字符上限">
              <n-input-number v-model:value="form.reasoning.context_max_chars" size="medium" :min="500" :max="10000" :step="500" class="w-full" />
            </FormField>
            <FormField label="检索短查询字符上限">
              <n-input-number v-model:value="form.reasoning.search_query_max_chars" size="medium" :min="100" :max="1000" :step="50" class="w-full" />
            </FormField>
          </div>
        </SettingsSection>

        <!-- Rerank -->
        <SettingsSection title="Rerank 二阶段精排">
          <div class="grid grid-cols-2 gap-x-6 gap-y-4">
            <FormField label="启用 Rerank" class="col-span-2">
              <n-switch v-model:value="form.rerank.enabled" />
              <span class="ml-3 text-sm text-gray-400">开启后使用硅基流动 Qwen Reranker 对检索候选结果精排</span>
            </FormField>
            <FormField label="模型名称">
              <n-input v-model:value="form.rerank.model" size="medium" placeholder="Qwen/Qwen3-Reranker-8B" />
            </FormField>
            <FormField label="API 地址">
              <n-input v-model:value="form.rerank.base_url" size="medium" placeholder="https://api.siliconflow.cn/v1" />
            </FormField>
            <FormField label="API Key" class="col-span-2">
              <n-input v-model:value="form.rerank.api_key" type="password" show-password-on="click" size="medium" placeholder="留空则复用 LLM/Embedding API Key" />
            </FormField>
            <FormField label="返回 Top-N">
              <n-input-number v-model:value="form.rerank.top_n" size="medium" :min="1" :max="50" class="w-full" />
            </FormField>
            <FormField label="候选池倍数">
              <n-input-number v-model:value="form.rerank.candidate_multiplier" size="medium" :min="1" :max="10" class="w-full" />
            </FormField>
            <FormField label="超时时间（秒）">
              <n-input-number v-model:value="form.rerank.timeout" size="medium" :min="5" :max="120" class="w-full" />
            </FormField>
            <FormField label="排序指令" class="col-span-2">
              <n-input v-model:value="form.rerank.instruction" type="textarea" size="medium" :autosize="{ minRows: 2, maxRows: 4 }" />
            </FormField>
          </div>
        </SettingsSection>

        <!-- MCP Web Search -->
        <SettingsSection title="MCP Web Search 网络搜索">
          <div class="grid grid-cols-2 gap-x-6 gap-y-4">
            <FormField label="启用网络搜索" class="col-span-2">
              <n-switch v-model:value="form.mcp.web_search_enabled" />
              <span class="ml-3 text-sm text-gray-400">开启后研究时可检索互联网</span>
            </FormField>
            <FormField label="Tavily API Key" class="col-span-2">
              <n-input v-model:value="form.mcp.tavily_api_key" type="password" show-password-on="click" size="medium" placeholder="在 tavily.com 注册获取（免费 1000次/月）" />
            </FormField>
            <FormField label="最大结果数">
              <n-input-number v-model:value="form.mcp.tavily_max_results" size="medium" :min="1" :max="20" class="w-full" />
            </FormField>
            <FormField label="超时时间（秒）">
              <n-input-number v-model:value="form.mcp.web_search_timeout" size="medium" :min="5" :max="120" class="w-full" />
            </FormField>
          </div>
        </SettingsSection>

        <!-- System Info -->
        <SystemInfo :info="store.systemInfo" :loading="store.isLoading" />
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { h, ref, reactive, watch, onMounted } from 'vue'
import { NIcon } from 'naive-ui'
import { SaveOutline, FlashOutline } from '@vicons/ionicons5'
import { useSettingsStore } from '@/stores/settings'
import { testConnection } from '@/api/settings'
import SettingsSection from '@/components/settings/SettingsSection.vue'
import SystemInfo from '@/components/settings/SystemInfo.vue'

// Simple inline form field component
const FormField = (props: { label: string; class?: string }, { slots }: any) => {
  return h('div', { class: props.class || '' }, [
    h('label', { class: 'block text-sm font-medium text-gray-600 mb-1.5' }, props.label),
    slots.default?.(),
  ])
}
FormField.props = ['label', 'class']

const store = useSettingsStore()

const llmProviders = [
  { label: 'SiliconFlow（硅基流动）', value: 'siliconflow' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Qwen（通义千问）', value: 'qwen' },
]

const testing = reactive({ llm: false, embedding: false, milvus: false, langsmith: false })
const testResult = ref<{ type: string; ok: boolean; msg: string } | null>(null)

async function runTest(service: 'llm' | 'embedding' | 'milvus' | 'langsmith') {
  testing[service] = true
  testResult.value = null
  try {
    const config = service === 'langsmith' ? { ...form.langsmith } : undefined
    const result = await testConnection(service, config)
    testResult.value = { type: service, ok: result.success, msg: result.data.message }
  } catch (e) {
    testResult.value = { type: service, ok: false, msg: e instanceof Error ? e.message : '测试请求失败' }
  } finally {
    testing[service] = false
  }
}

function testLLM() { runTest('llm') }
function testEmbedding() { runTest('embedding') }
function testMilvus() { runTest('milvus') }
function testLangSmith() { runTest('langsmith') }

const form = reactive({
  llm: { provider: 'siliconflow', model: '', api_key: '', base_url: '', temperature: 0.3, max_tokens: 4096 },
  embedding: { mode: 'api', model: '', api_key: '', device: 'cpu', api_base_url: '', query_max_chars: 500 },
  retrieval: { top_k: 5, max_retries: 3, critique_threshold: 0.6, rrf_k: 60, vector_backend: 'chroma' },
  reasoning: { enabled: true, max_hops: 3, context_max_chars: 3000, search_query_max_chars: 400 },
  rerank: { enabled: false, provider: 'siliconflow', model: 'Qwen/Qwen3-Reranker-8B', api_key: '', base_url: 'https://api.siliconflow.cn/v1', top_n: 5, candidate_multiplier: 4, timeout: 30, instruction: '请根据查询内容判断文档与查询的相关性，并按相关性从高到低排序。' },
  milvus: { uri: '', token: '', host: 'localhost', port: 19530, collection_name: 'research_docs' },
  mcp: { web_search_enabled: false, tavily_api_key: '', tavily_max_results: 5, web_search_timeout: 30.0 },
  langsmith: { tracing: false, tracing_v2: false, api_key: '', project: 'deep-research-agent', endpoint: 'https://api.smith.langchain.com' },
})

watch(() => store.settings, (s) => {
  if (s) {
    Object.assign(form.llm, s.llm)
    Object.assign(form.embedding, s.embedding)
    Object.assign(form.retrieval, s.retrieval)
    if ((s as any).reasoning) Object.assign(form.reasoning, (s as any).reasoning)
    if ((s as any).rerank) Object.assign(form.rerank, (s as any).rerank)
    if ((s as any).milvus) Object.assign(form.milvus, (s as any).milvus)
    if ((s as any).mcp) Object.assign(form.mcp, (s as any).mcp)
    if ((s as any).langsmith) Object.assign(form.langsmith, (s as any).langsmith)
  }
}, { immediate: true })

onMounted(() => { store.loadSettings() })

function onSave() {
  store.saveSettings({
    llm: form.llm,
    embedding: form.embedding,
    retrieval: form.retrieval,
    reasoning: form.reasoning,
    rerank: form.rerank,
    milvus: form.retrieval.vector_backend === 'milvus' ? form.milvus : undefined,
    mcp: form.mcp,
    langsmith: { ...form.langsmith, tracing_v2: form.langsmith.tracing },
  })
}
</script>
