<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-800">⚙️ 系统设置</h1>
        <p class="text-sm text-gray-400">配置 LLM、嵌入模型和检索参数</p>
      </div>
      <n-button type="primary" :loading="store.isSaving" @click="onSave">
        <template #icon><n-icon><save-outline /></n-icon></template>
        保存配置
      </n-button>
    </div>

    <n-spin :show="store.isLoading">
      <n-alert v-if="store.error" type="error" :bordered="false" class="mb-4" @close="store.error = null">
        {{ store.error }}
      </n-alert>
      <n-alert v-if="store.successMsg" type="success" :bordered="false" class="mb-4">
        {{ store.successMsg }}
      </n-alert>
      <n-alert v-if="testResult" :type="testResult.ok ? 'success' : 'error'" :bordered="false" class="mb-4" @close="testResult = null">
        <template #header>
          {{ testResult.ok ? '✓ 连接成功' : '✗ 连接失败' }}
        </template>
        {{ testResult.msg }}
      </n-alert>

      <div v-if="store.settings">
        <!-- LLM -->
        <SettingsSection title="LLM 配置">
          <template #actions>
            <n-button size="tiny" :loading="testing.llm" @click="testLLM">
              {{ testing.llm ? '测试中...' : '测试连接' }}
            </n-button>
          </template>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">提供商</label>
              <n-select v-model:value="form.llm.provider" :options="llmProviders" size="small" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">模型</label>
              <n-input v-model:value="form.llm.model" size="small" />
            </div>
            <div class="col-span-2">
              <label class="text-xs text-gray-500 mb-1 block">API Key</label>
              <n-input v-model:value="form.llm.api_key" type="password" show-password-on="click" size="small" placeholder="留空则不修改" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">Temperature: {{ form.llm.temperature }}</label>
              <n-slider v-model:value="form.llm.temperature" :min="0" :max="2" :step="0.1" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">Max Tokens</label>
              <n-input-number v-model:value="form.llm.max_tokens" size="small" :min="256" :max="32768" />
            </div>
          </div>
        </SettingsSection>

        <!-- Embedding -->
        <SettingsSection title="嵌入模型">
          <template #actions>
            <n-button size="tiny" :loading="testing.embedding" @click="testEmbedding">
              {{ testing.embedding ? '测试中...' : '测试连接' }}
            </n-button>
          </template>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">模式</label>
              <n-radio-group v-model:value="form.embedding.mode">
                <n-radio value="local">本地</n-radio>
                <n-radio value="api">API</n-radio>
              </n-radio-group>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">模型</label>
              <n-input v-model:value="form.embedding.model" size="small" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">API 地址</label>
              <n-input v-model:value="form.embedding.api_base_url" size="small" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">API Key</label>
              <n-input v-model:value="form.embedding.api_key" type="password" show-password-on="click" size="small" placeholder="留空则不修改" />
            </div>
          </div>
        </SettingsSection>

        <!-- Retrieval -->
        <SettingsSection title="检索配置">
          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">Top-K</label>
              <n-input-number v-model:value="form.retrieval.top_k" size="small" :min="1" :max="50" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">最大重试</label>
              <n-input-number v-model:value="form.retrieval.max_retries" size="small" :min="0" :max="10" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">相似度阈值: {{ form.retrieval.critique_threshold }}</label>
              <n-slider v-model:value="form.retrieval.critique_threshold" :min="0.3" :max="0.95" :step="0.05" />
            </div>
          </div>
        </SettingsSection>

        <!-- Vector Store -->
        <SettingsSection title="向量存储">
          <template #actions>
            <n-button size="tiny" :loading="testing.milvus" @click="testMilvus">
              {{ testing.milvus ? '测试中...' : '测试连接' }}
            </n-button>
          </template>
          <div class="mb-4">
            <label class="text-xs text-gray-500 mb-2 block">存储后端</label>
            <n-radio-group v-model:value="form.retrieval.vector_backend">
              <n-radio value="chroma">ChromaDB（本地嵌入式）</n-radio>
              <n-radio value="milvus">Milvus（Zilliz Cloud 或自建）</n-radio>
            </n-radio-group>
          </div>

          <div v-if="form.retrieval.vector_backend === 'milvus'" class="p-3 bg-gray-50 rounded-lg space-y-3">
            <!-- Zilliz Cloud -->
            <div>
              <label class="text-xs font-medium text-gray-600 mb-1 block">Zilliz Cloud（托管服务，推荐）</label>
              <p class="text-xs text-gray-400 mb-2">在 zilliz.com 注册获取，免费额度足以开发使用</p>
              <div class="grid grid-cols-1 gap-2">
                <n-input v-model:value="form.milvus.uri" size="small" placeholder="https://in03-xxxx.api.vectordb.zillizcloud.com">
                  <template #prefix>
                    <span class="text-xs text-gray-400 w-10 inline-block">URI</span>
                  </template>
                </n-input>
                <n-input v-model:value="form.milvus.token" type="password" show-password-on="click" size="small" placeholder="API Token，留空则不修改">
                  <template #prefix>
                    <span class="text-xs text-gray-400 w-10 inline-block">Token</span>
                  </template>
                </n-input>
              </div>
            </div>

            <!-- Self-hosted -->
            <div class="pt-2 border-t border-gray-200">
              <label class="text-xs font-medium text-gray-500 mb-1 block">自建 Milvus（不使用 Zilliz Cloud 时填写）</label>
              <div class="grid grid-cols-2 gap-2">
                <n-input v-model:value="form.milvus.host" size="small" placeholder="localhost">
                  <template #prefix>
                    <span class="text-xs text-gray-400 w-10 inline-block">Host</span>
                  </template>
                </n-input>
                <n-input-number v-model:value="form.milvus.port" size="small" :min="1" :max="65535" placeholder="19530" />
              </div>
            </div>
          </div>

          <n-alert type="warning" :bordered="false" class="mt-3 text-xs">
            切换存储后端需重启后端生效，且需要重新索引文档。
          </n-alert>
        </SettingsSection>
      </div>

      <SystemInfo :info="store.systemInfo" :loading="store.isLoading" />
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { NIcon } from 'naive-ui'
import { SaveOutline } from '@vicons/ionicons5'
import { useSettingsStore } from '@/stores/settings'
import { testConnection } from '@/api/settings'
import SettingsSection from '@/components/settings/SettingsSection.vue'
import SystemInfo from '@/components/settings/SystemInfo.vue'

const store = useSettingsStore()

const llmProviders = [
  { label: 'SiliconFlow', value: 'siliconflow' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Qwen (通义千问)', value: 'qwen' },
]

const testing = reactive({ llm: false, embedding: false, milvus: false })
const testResult = ref<{ type: string; ok: boolean; msg: string } | null>(null)

async function runTest(service: 'llm' | 'embedding' | 'milvus') {
  testing[service] = true
  testResult.value = null
  try {
    const result = await testConnection(service)
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

const form = reactive({
  llm: { provider: 'siliconflow', model: '', api_key: '', base_url: '', temperature: 0.3, max_tokens: 4096 },
  embedding: { mode: 'api', model: '', api_key: '', device: 'cpu', api_base_url: '' },
  retrieval: { top_k: 5, max_retries: 3, critique_threshold: 0.6, rrf_k: 60, vector_backend: 'chroma' },
  milvus: { uri: '', token: '', host: 'localhost', port: 19530, collection_name: 'research_docs' },
})

watch(() => store.settings, (s) => {
  if (s) {
    Object.assign(form.llm, s.llm)
    Object.assign(form.embedding, s.embedding)
    Object.assign(form.retrieval, s.retrieval)
    if ((s as any).milvus) Object.assign(form.milvus, (s as any).milvus)
  }
}, { immediate: true })

onMounted(() => { store.loadSettings() })

function onSave() {
  store.saveSettings({
    llm: form.llm,
    embedding: form.embedding,
    retrieval: form.retrieval,
    milvus: form.retrieval.vector_backend === 'milvus' ? form.milvus : undefined,
  })
}
</script>
