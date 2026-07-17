import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { ResearchMode } from '@/api/research'

export type PhaseState = 'waiting' | 'running' | 'complete' | 'error'

export interface PlanItem {
  index: number
  question: string
  strategy: string
  rationale: string
  hop?: number
  dependsOn?: number[]
}

export interface CritiqueItem {
  step: number
  attempt: number
  score: number
  relevance: number
  completeness: number
  passed: boolean
  reasoning: string
  retrySuggestion: string
}

export interface RetrievalProgress {
  step: number
  total: number
  strategy: string
  results: number
  topScore: number
  topPreview: string
  retry: number
}

export interface EventLogItem {
  elapsed: number
  eventType: string
  summary: string
  data: Record<string, unknown>
}

export interface RetryHistoryItem {
  step: number
  attempt: number
  score: number
  suggestion: string
}

export interface Source {
  chunk_id: string
  score: number
  combined_score?: number
  metadata: Record<string, unknown>
  content: string
}

export interface WebSearchResultItem {
  title: string
  url: string
  content: string
  score: number
}

export interface ReasoningContextItem {
  step: number
  hop: number
  dependsOn: number[]
  summary: string
  entityCount: number
  factCount: number
  lowConfidence: boolean
}

export interface BackendTimingItem {
  category: string
  operation: string
  durationMs: number
  step?: number
  attempt?: number
  details: Record<string, unknown>
}

export const useResearchStore = defineStore('research', () => {
  const STORAGE_KEY = 'deep-research:research-state:v1'
  const query = ref('')
  const taskId = ref<string | null>(null)
  const isRunning = ref(false)
  const isCancelled = ref(false)
  const error = ref<string | null>(null)
  const researchMode = ref<ResearchMode>('auto')
  const maxHops = ref(3)

  const report = ref('')
  const streamingReport = ref('')
  const sources = ref<Source[]>([])

  const phaseStates = ref<Record<string, PhaseState>>({
    decomposition: 'waiting',
    retrieval: 'waiting',
    critique: 'waiting',
    synthesis: 'waiting',
  })

  const progressValue = ref(0)
  const currentDetail = ref('')

  const researchPlan = ref<PlanItem[]>([])
  const critiqueResults = ref<CritiqueItem[]>([])
  const retrievalProgress = ref<RetrievalProgress | null>(null)
  const eventLog = ref<EventLogItem[]>([])
  const retryHistory = ref<RetryHistoryItem[]>([])

  const startedAt = ref<number | null>(null)
  const finishedAt = ref<number | null>(null)
  const phaseDurations = ref<Record<string, number>>({})
  const phaseStartTimes = ref<Record<string, number>>({})

  const previousStep = ref('')
  const webSearchResults = ref<WebSearchResultItem[]>([])
  const reasoningContexts = ref<ReasoningContextItem[]>([])
  const backendTimings = ref<BackendTimingItem[]>([])
  const activeRetrievalSteps = ref<number[]>([])
  const activeCritiqueSteps = ref<number[]>([])

  function snapshot() {
    return {
      query: query.value,
      taskId: taskId.value,
      isRunning: isRunning.value,
      isCancelled: isCancelled.value,
      error: error.value,
      researchMode: researchMode.value,
      maxHops: maxHops.value,
      report: report.value,
      streamingReport: streamingReport.value,
      sources: sources.value,
      phaseStates: phaseStates.value,
      progressValue: progressValue.value,
      currentDetail: currentDetail.value,
      researchPlan: researchPlan.value,
      critiqueResults: critiqueResults.value,
      retrievalProgress: retrievalProgress.value,
      eventLog: eventLog.value,
      retryHistory: retryHistory.value,
      startedAt: startedAt.value,
      finishedAt: finishedAt.value,
      phaseDurations: phaseDurations.value,
      phaseStartTimes: phaseStartTimes.value,
      previousStep: previousStep.value,
      webSearchResults: webSearchResults.value,
      reasoningContexts: reasoningContexts.value,
      backendTimings: backendTimings.value,
      activeRetrievalSteps: activeRetrievalSteps.value,
      activeCritiqueSteps: activeCritiqueSteps.value,
    }
  }

  function persist() {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot()))
    } catch {
      // Persistence is best-effort (for example, private browsing quotas).
    }
  }

  function restore() {
    if (typeof window === 'undefined') return
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const saved = JSON.parse(raw) as Partial<ReturnType<typeof snapshot>>
      if (typeof saved.query === 'string') query.value = saved.query
      if (typeof saved.taskId === 'string' || saved.taskId === null) taskId.value = saved.taskId
      if (typeof saved.isRunning === 'boolean') isRunning.value = saved.isRunning
      if (typeof saved.isCancelled === 'boolean') isCancelled.value = saved.isCancelled
      if (typeof saved.error === 'string' || saved.error === null) error.value = saved.error
      if (saved.researchMode) researchMode.value = saved.researchMode
      if (typeof saved.maxHops === 'number') maxHops.value = saved.maxHops
      if (typeof saved.report === 'string') report.value = saved.report
      if (typeof saved.streamingReport === 'string') streamingReport.value = saved.streamingReport
      if (Array.isArray(saved.sources)) sources.value = saved.sources
      if (saved.phaseStates) phaseStates.value = saved.phaseStates
      if (typeof saved.progressValue === 'number') progressValue.value = saved.progressValue
      if (typeof saved.currentDetail === 'string') currentDetail.value = saved.currentDetail
      if (Array.isArray(saved.researchPlan)) researchPlan.value = saved.researchPlan
      if (Array.isArray(saved.critiqueResults)) critiqueResults.value = saved.critiqueResults
      if (saved.retrievalProgress !== undefined) retrievalProgress.value = saved.retrievalProgress
      if (Array.isArray(saved.eventLog)) eventLog.value = saved.eventLog
      if (Array.isArray(saved.retryHistory)) retryHistory.value = saved.retryHistory
      if (typeof saved.startedAt === 'number' || saved.startedAt === null) startedAt.value = saved.startedAt
      if (typeof saved.finishedAt === 'number' || saved.finishedAt === null) finishedAt.value = saved.finishedAt
      if (saved.phaseDurations) phaseDurations.value = saved.phaseDurations
      if (saved.phaseStartTimes) phaseStartTimes.value = saved.phaseStartTimes
      if (typeof saved.previousStep === 'string') previousStep.value = saved.previousStep
      if (Array.isArray(saved.webSearchResults)) webSearchResults.value = saved.webSearchResults
      if (Array.isArray(saved.reasoningContexts)) reasoningContexts.value = saved.reasoningContexts
      if (Array.isArray(saved.backendTimings)) backendTimings.value = saved.backendTimings
      if (Array.isArray(saved.activeRetrievalSteps)) activeRetrievalSteps.value = saved.activeRetrievalSteps
      if (Array.isArray(saved.activeCritiqueSteps)) activeCritiqueSteps.value = saved.activeCritiqueSteps
      // Older snapshots predate finishedAt. Freeze their completed timer at
      // the best duration available instead of letting "总用时" keep growing.
      if (!isRunning.value && startedAt.value && !finishedAt.value) {
        const measuredSeconds = Object.values(phaseDurations.value).reduce((sum, value) => sum + value, 0)
        finishedAt.value = startedAt.value + measuredSeconds * 1000
      }
    } catch {
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }

  const currentStep = computed(() => {
    if (isCancelled.value) return 'cancelled'
    if (phaseStates.value.synthesis === 'complete') return 'done'
    if (phaseStates.value.synthesis === 'running') return 'synthesizing'
    if (phaseStates.value.critique === 'running') return 'evaluating'
    if (phaseStates.value.retrieval === 'running') return 'retrieving'
    if (phaseStates.value.decomposition === 'running') return 'planning'
    return ''
  })

  const phaseLabels: Record<string, string> = {
    decomposition: '拆解问题',
    retrieval: '检索',
    critique: '评估',
    synthesis: '合成报告',
  }

  function reset() {
    query.value = ''
    taskId.value = null
    isRunning.value = false
    isCancelled.value = false
    error.value = null
    report.value = ''
    streamingReport.value = ''
    sources.value = []
    phaseStates.value = {
      decomposition: 'waiting',
      retrieval: 'waiting',
      critique: 'waiting',
      synthesis: 'waiting',
    }
    progressValue.value = 0
    currentDetail.value = ''
    researchPlan.value = []
    critiqueResults.value = []
    retrievalProgress.value = null
    eventLog.value = []
    retryHistory.value = []
    startedAt.value = null
    finishedAt.value = null
    phaseDurations.value = {}
    phaseStartTimes.value = {}
    previousStep.value = ''
    webSearchResults.value = []
    reasoningContexts.value = []
    backendTimings.value = []
    activeRetrievalSteps.value = []
    activeCritiqueSteps.value = []
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }

  const strategyLabels: Record<string, string> = {
    semantic: '语义检索',
    keyword: '关键词检索',
    hybrid: '混合检索',
  }

  const timingOperationLabels: Record<string, string> = {
    decomposition: '问题拆解',
    research_layer: '依赖层研究',
    research_step: '子问题研究',
    local_retrieval: '本地检索',
    web_search: '联网搜索',
    strategy_selection: '策略选择',
    query_rewrite: '查询改写',
    reasoning_query: '多跳查询',
    critique: '质量评估',
    context_extraction: '上下文提取',
    synthesis: '报告生成',
  }

  function strategyLabel(strategy: unknown): string {
    const value = String(strategy || '')
    return strategyLabels[value] || value
  }

  function timingOperationLabel(operation: unknown): string {
    const value = String(operation || '')
    return timingOperationLabels[value] || value
  }

  function summarizeEvent(eventType: string, data: Record<string, unknown>): string {
    switch (eventType) {
      case 'research_plan_start':
        return `开始拆解: ${(data.query as string || '').slice(0, 60)}`
      case 'research_plan_chunk':
        return `子问题 #${data.index}：${(data.question as string || '').slice(0, 50)}（策略：${strategyLabel(data.strategy)}）`
      case 'retrieval_start':
        return `检索 ${data.step}/${data.total}（策略：${strategyLabel(data.strategy)}）`
      case 'retrieval_result':
        return `检索完成：${data.result_count} 条结果，最高分 ${(data.top_score as number || 0).toFixed(3)}`
      case 'critique_start':
        return `评估检索质量 (步骤 ${data.step})`
      case 'critique_result': {
        const s = data.composite_score as number || 0
        const p = data.passed ? '通过' : '未通过'
        return `评估结果：${s.toFixed(3)}【${p}】`
      }
      case 'retry_triggered':
        return `触发重试 #${data.count}`
      case 'synthesis_start':
        return `开始生成报告 (${data.total_steps} 步骤聚合)`
      case 'reasoning_context':
        return `步骤 ${data.step} 上下文已提取: ${data.entity_count || 0} 个实体, ${data.fact_count || 0} 条事实`
      case 'reasoning_query':
        return `第 ${data.hop || 1} 跳已生成短查询（${data.context_chars || 0} → ${data.query_chars || 0} 字符）`
      case 'research_layer_start':
        return `开始依赖层: 步骤 ${((data.steps as number[]) || []).join('、')}（并发 ${data.concurrency || 1}）`
      case 'timing':
        return `${timingOperationLabel(data.operation || data.category)}：${Number(data.duration_ms || 0).toFixed(1)}ms`
      case 'synthesis_chunk':
        return `报告片段: ${(data.text as string || '').slice(0, 60)}...`
      case 'web_search_start':
        return `联网搜索: ${(data.query as string || '').slice(0, 50)}`
      case 'web_search_result':
        return `联网搜索完成: ${data.result_count} 条结果`
      case 'retrieval_combined':
        return `检索汇总: 本地 ${data.local_count} + 网络 ${data.web_count} = ${data.total_count} 条`
      case 'done':
        return `完成, 报告长度: ${data.report_length || 0} 字符`
      case 'error':
        return `错误: ${(data.message as string || '').slice(0, 80)}`
      default:
        return eventType
    }
  }

  function estimateProgress(eventType: string): number {
    const estimates: Record<string, number> = {
      'research_plan_start': 0.05,
      'research_plan_chunk': 0.10,
      'retrieval_start': 0.15,
      'retrieval_result': 0.35,
      'critique_start': 0.40,
      'critique_result': 0.50,
      'retry_triggered': 0.35,
      'synthesis_start': 0.60,
      'reasoning_context': 0.55,
      'reasoning_query': 0.56,
      'synthesis_chunk': 0.75,
      'done': 1.0,
      'error': 0,
    }
    return estimates[eventType] ?? progressValue.value
  }

  function recordPhaseTime(key: string) {
    if (key in phaseStartTimes.value) {
      const start = phaseStartTimes.value[key]
      delete phaseStartTimes.value[key]
      phaseDurations.value[key] = (phaseDurations.value[key] || 0) + (Date.now() - start) / 1000
    }
  }

  function handleEvent(eventType: string, data: Record<string, unknown>) {
    // Replayed streams begin with this event. Clear stale entries before
    // recording it so the start event remains visible in the timeline.
    if (eventType === 'research_plan_start') {
      eventLog.value = []
    }
    const elapsed = startedAt.value ? (Date.now() - startedAt.value) / 1000 : 0
    const summary = summarizeEvent(eventType, data)
    eventLog.value.push({ elapsed, eventType, summary, data })
    if (eventLog.value.length > 500) {
      eventLog.value = eventLog.value.slice(-500)
    }

    if (typeof data.progress === 'number') {
      progressValue.value = Math.max(progressValue.value, data.progress as number)
    } else {
      progressValue.value = Math.max(progressValue.value, estimateProgress(eventType))
    }

    switch (eventType) {
      case 'research_plan_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在拆解研究问题...'
        researchPlan.value = []
        startedAt.value ??= Date.now()
        finishedAt.value = null
        phaseDurations.value = {}
        phaseStartTimes.value = {}
        retryHistory.value = []
        phaseStates.value = {
          decomposition: 'running',
          retrieval: 'waiting',
          critique: 'waiting',
          synthesis: 'waiting',
        }
        phaseStartTimes.value['decomposition'] = Date.now()
        progressValue.value = Math.max(progressValue.value, 0.05)
        researchMode.value = (data.research_mode as ResearchMode) || researchMode.value
        maxHops.value = (data.max_hops as number) || maxHops.value
        break

      case 'research_plan_chunk':
        researchPlan.value.push({
          index: data.index as number,
          question: data.question as string,
          strategy: data.strategy as string,
          rationale: data.rationale as string || '',
          hop: data.hop as number || 1,
          dependsOn: (data.depends_on as number[]) || [],
        })
        break

      case 'retrieval_start': {
        previousStep.value = currentStep.value
        const step = data.step as number
        const total = data.total as number
        const strategyName: Record<string, string> = {
          semantic: '语义', keyword: '关键词', hybrid: '混合'
        }
        const strategyLabel = strategyName[data.strategy as string] || (data.strategy as string)
        currentDetail.value = `正在检索 子问题 ${step}/${total}（${strategyLabel}策略）`
        retrievalProgress.value = {
          step, total,
          strategy: data.strategy as string,
          results: 0, topScore: 0, topPreview: '',
          retry: (data.retry_count as number) || 0,
        }
        recordPhaseTime('decomposition')
        phaseStates.value.decomposition = 'complete'
        phaseStartTimes.value[`retrieval_${step}`] = Date.now()
        if (!activeRetrievalSteps.value.includes(step)) activeRetrievalSteps.value.push(step)
        phaseStates.value.retrieval = 'running'
        phaseStates.value.critique = activeCritiqueSteps.value.length ? 'running' : 'waiting'
        phaseStates.value.synthesis = 'waiting'
        break
      }

      case 'retrieval_result': {
        const rp = retrievalProgress.value
        if (rp?.step === Number(data.step)) {
          rp.results = data.result_count as number
          rp.topScore = data.top_score as number
          rp.topPreview = data.top_preview as string || ''
        }
        currentDetail.value = `检索完成，找到 ${data.result_count} 条结果（最高相似度: ${(data.top_score as number || 0).toFixed(2)}）`
        break
      }

      case 'critique_start': {
        const step = Number(data.step)
        previousStep.value = currentStep.value
        currentDetail.value = `正在评估步骤 ${step} 的检索质量...`
        phaseStartTimes.value[`critique_${step}`] = Date.now()
        if (!activeCritiqueSteps.value.includes(step)) activeCritiqueSteps.value.push(step)
        phaseStates.value.retrieval = activeRetrievalSteps.value.length ? 'running' : 'complete'
        phaseStates.value.critique = 'running'
        break
      }

      case 'critique_result': {
        const passed = data.passed as boolean
        const step = data.step as number
        const attempt = critiqueResults.value.filter(item => item.step === step).length + 1
        critiqueResults.value.push({
          step,
          attempt,
          score: data.composite_score as number,
          relevance: data.relevance as number,
          completeness: data.completeness as number,
          passed,
          reasoning: data.reasoning as string || '',
          retrySuggestion: data.retry_suggestion as string || '',
        })
        currentDetail.value = `质量评估: ${(data.composite_score as number).toFixed(2)} 分 — ${passed ? '通过' : '不通过'}`
        recordPhaseTime(`critique_${step}`)
        activeCritiqueSteps.value = activeCritiqueSteps.value.filter(item => item !== step)
        phaseStates.value.critique = activeCritiqueSteps.value.length ? 'running' : 'complete'
        // Synthesis starts only after all planned steps are complete.
        phaseStates.value.synthesis = 'waiting'
        break
      }

      case 'web_search_start': {
        previousStep.value = currentStep.value
        currentDetail.value = `正在联网搜索: ${(data.query as string || '').slice(0, 40)}...`
        webSearchResults.value = []
        recordPhaseTime('decomposition')
        phaseStates.value.decomposition = 'complete'
        phaseStates.value.retrieval = 'running'
        const step = Number(data.step || retrievalProgress.value?.step || 1)
        const timingKey = `retrieval_${step}`
        phaseStartTimes.value[timingKey] ??= Date.now()
        if (!activeRetrievalSteps.value.includes(step)) activeRetrievalSteps.value.push(step)
        break
      }

      case 'reasoning_context':
        reasoningContexts.value.push({
          step: data.step as number,
          hop: (data.hop as number) || 1,
          dependsOn: (data.depends_on as number[]) || [],
          summary: (data.summary as string) || '',
          entityCount: (data.entity_count as number) || 0,
          factCount: (data.fact_count as number) || 0,
          lowConfidence: Boolean(data.low_confidence),
        })
        currentDetail.value = `已提取第 ${data.step} 步的研究上下文`
        break

      case 'timing':
        backendTimings.value.push({
          category: String(data.category || 'stage'),
          operation: String(data.operation || 'unknown'),
          durationMs: Number(data.duration_ms || 0),
          step: data.step == null ? undefined : Number(data.step),
          attempt: data.attempt == null ? undefined : Number(data.attempt),
          details: (data.details as Record<string, unknown>) || {},
        })
        if (backendTimings.value.length > 300) {
          backendTimings.value = backendTimings.value.slice(-300)
        }
        break

      case 'web_search_result': {
        const results = (data.results as WebSearchResultItem[]) || []
        webSearchResults.value = results
        currentDetail.value = `联网搜索完成，找到 ${data.result_count} 条结果`
        break
      }

      case 'retrieval_combined': {
        const local = data.local_count as number || 0
        const web = data.web_count as number || 0
        currentDetail.value = `检索完成: 本地 ${local} + 网络 ${web} = ${data.total_count} 条`
        recordPhaseTime(`retrieval_${data.step}`)
        activeRetrievalSteps.value = activeRetrievalSteps.value.filter(item => item !== Number(data.step))
        phaseStates.value.retrieval = activeRetrievalSteps.value.length ? 'running' : 'complete'
        break
      }

      case 'retry_triggered': {
        previousStep.value = currentStep.value
        const count = data.count as number
        const step = (data.step as number) || retrievalProgress.value?.step || 1
        currentDetail.value = `检索质量不达标，正在第 ${count} 次重试（改写查询）...`
        const stepCritiques = critiqueResults.value.filter(item => item.step === step)
        const lastCritique = stepCritiques[stepCritiques.length - 1]
        retryHistory.value.push({
          step,
          attempt: count,
          score: lastCritique?.score ?? 0,
          suggestion: lastCritique?.retrySuggestion ?? '',
        })
        phaseStates.value.critique = activeCritiqueSteps.value.length ? 'running' : 'complete'
        phaseStates.value.retrieval = 'running'
        phaseStates.value.synthesis = 'waiting'
        break
      }

      case 'synthesis_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在聚合多源信息，生成研究报告...'
        phaseStartTimes.value['synthesis'] = Date.now()
        activeRetrievalSteps.value = []
        activeCritiqueSteps.value = []
        phaseStates.value.critique = 'complete'
        phaseStates.value.synthesis = 'running'
        break

      case 'synthesis_chunk':
        streamingReport.value += (data.text as string || '')
        break

      case 'done':
        phaseStates.value.synthesis = 'complete'
        progressValue.value = 1.0
        currentDetail.value = `研究完成，报告共 ${data.report_length || 0} 字符`
        recordPhaseTime('synthesis')
        if (streamingReport.value && !report.value) {
          report.value = streamingReport.value
        }
        isRunning.value = false
        finishedAt.value = Date.now()
        break

      case 'error':
        error.value = data.message as string || '发生未知错误'
        markCurrentPhaseError()
        isRunning.value = false
        finishedAt.value = Date.now()
        break

      case 'cancelled':
        isCancelled.value = true
        isRunning.value = false
        markCurrentPhaseError()
        finishedAt.value = Date.now()
        if (streamingReport.value && !report.value) {
          report.value = streamingReport.value
        }
        break
    }
    persist()
  }

  function markCurrentPhaseError() {
    const phaseOrder = ['synthesis', 'critique', 'retrieval', 'decomposition']
    const runningPhase = phaseOrder.find(key => phaseStates.value[key] === 'running')
    if (runningPhase) {
      phaseStates.value[runningPhase] = 'error'
    }
  }

  function setQuery(q: string) {
    query.value = q
    persist()
  }

  function startResearch(tid: string, mode: ResearchMode = 'auto', hops: number = 3) {
    taskId.value = tid
    isRunning.value = true
    isCancelled.value = false
    error.value = null
    report.value = ''
    streamingReport.value = ''
    sources.value = []
    researchMode.value = mode
    maxHops.value = hops
    startedAt.value = Date.now()
    finishedAt.value = null
    persist()
  }

  function setSources(s: Source[]) {
    sources.value = s
    persist()
  }

  function setFinalReport(text: string, srcs: Source[]) {
    report.value = text
    sources.value = srcs
    isRunning.value = false
    error.value = null
    progressValue.value = 1
    phaseStates.value = {
      decomposition: 'complete',
      retrieval: 'complete',
      critique: 'complete',
      synthesis: 'complete',
    }
    currentDetail.value = `研究完成，报告共 ${text.length} 字符`
    finishedAt.value ??= Date.now()
    persist()
  }

  function prepareForReplay() {
    isRunning.value = true
    isCancelled.value = false
    error.value = null
    report.value = ''
    streamingReport.value = ''
    sources.value = []
    phaseStates.value = {
      decomposition: 'waiting',
      retrieval: 'waiting',
      critique: 'waiting',
      synthesis: 'waiting',
    }
    currentDetail.value = '正在恢复研究进度...'
    researchPlan.value = []
    critiqueResults.value = []
    retrievalProgress.value = null
    eventLog.value = []
    retryHistory.value = []
    phaseDurations.value = {}
    phaseStartTimes.value = {}
    previousStep.value = ''
    webSearchResults.value = []
    reasoningContexts.value = []
    backendTimings.value = []
    activeRetrievalSteps.value = []
    activeCritiqueSteps.value = []
    finishedAt.value = null
    persist()
  }

  function setFailure(message: string) {
    error.value = message
    markCurrentPhaseError()
    isRunning.value = false
    finishedAt.value = Date.now()
    if (streamingReport.value && !report.value) {
      report.value = streamingReport.value
    }
    persist()
  }

  function setCancelled(message = '研究已被用户取消') {
    isCancelled.value = true
    isRunning.value = false
    currentDetail.value = message
    markCurrentPhaseError()
    finishedAt.value = Date.now()
    if (streamingReport.value && !report.value) {
      report.value = streamingReport.value
    }
    persist()
  }

  restore()
  watch(snapshot, persist, { deep: true })

  return {
    query, taskId, isRunning, isCancelled, error, researchMode, maxHops,
    report, streamingReport, sources,
    phaseStates, progressValue, currentDetail,
    researchPlan, critiqueResults, retrievalProgress, eventLog, retryHistory,
    startedAt, finishedAt, phaseDurations, phaseStartTimes, previousStep, webSearchResults,
    reasoningContexts, backendTimings, activeRetrievalSteps, activeCritiqueSteps,
    currentStep, phaseLabels,
    reset, handleEvent, setQuery, startResearch, setSources, setFinalReport,
    prepareForReplay, setFailure, setCancelled, persist,
  }
})
