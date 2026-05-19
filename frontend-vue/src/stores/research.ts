import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type PhaseState = 'waiting' | 'running' | 'complete' | 'error'

export interface PlanItem {
  index: number
  question: string
  strategy: string
  rationale: string
}

export interface CritiqueItem {
  step: number
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

export const useResearchStore = defineStore('research', () => {
  const query = ref('')
  const taskId = ref<string | null>(null)
  const isRunning = ref(false)
  const isCancelled = ref(false)
  const error = ref<string | null>(null)

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
  const phaseDurations = ref<Record<string, number>>({})
  const phaseStartTimes = ref<Record<string, number>>({})

  const previousStep = ref('')
  const webSearchResults = ref<WebSearchResultItem[]>([])

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
    phaseDurations.value = {}
    phaseStartTimes.value = {}
    previousStep.value = ''
    webSearchResults.value = []
  }

  function summarizeEvent(eventType: string, data: Record<string, unknown>): string {
    switch (eventType) {
      case 'research_plan_start':
        return `开始拆解: ${(data.query as string || '').slice(0, 60)}`
      case 'research_plan_chunk':
        return `子问题 #${data.index}: ${(data.question as string || '').slice(0, 50)} (策略: ${data.strategy})`
      case 'retrieval_start':
        return `检索 ${data.step}/${data.total} (策略: ${data.strategy})`
      case 'retrieval_result':
        return `检索完成: ${data.result_count} 条结果, top=${(data.top_score as number || 0).toFixed(3)}`
      case 'critique_start':
        return `评估检索质量 (步骤 ${data.step})`
      case 'critique_result': {
        const s = data.composite_score as number || 0
        const p = data.passed ? 'PASS' : 'FAIL'
        return `评估结果: ${s.toFixed(3)} [${p}]`
      }
      case 'retry_triggered':
        return `触发重试 #${data.count}`
      case 'synthesis_start':
        return `开始生成报告 (${data.total_steps} 步骤聚合)`
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
      phaseDurations.value[key] = (Date.now() - start) / 1000
    }
  }

  function handleEvent(eventType: string, data: Record<string, unknown>) {
    const elapsed = startedAt.value ? (Date.now() - startedAt.value) / 1000 : 0
    const summary = summarizeEvent(eventType, data)
    eventLog.value.push({ elapsed, eventType, summary, data })
    if (eventLog.value.length > 500) {
      eventLog.value = eventLog.value.slice(-500)
    }

    if (typeof data.progress === 'number') {
      progressValue.value = data.progress as number
    } else {
      progressValue.value = estimateProgress(eventType)
    }

    switch (eventType) {
      case 'research_plan_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在拆解研究问题...'
        researchPlan.value = []
        startedAt.value = Date.now()
        eventLog.value = []
        phaseDurations.value = {}
        retryHistory.value = []
        phaseStates.value = {
          decomposition: 'running',
          retrieval: 'waiting',
          critique: 'waiting',
          synthesis: 'waiting',
        }
        phaseStartTimes.value['decomposition'] = Date.now()
        progressValue.value = 0.05
        break

      case 'research_plan_chunk':
        researchPlan.value.push({
          index: data.index as number,
          question: data.question as string,
          strategy: data.strategy as string,
          rationale: data.rationale as string || '',
        })
        recordPhaseTime('decomposition')
        phaseStates.value.decomposition = 'complete'
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
        phaseStartTimes.value[`retrieval_${step}`] = Date.now()
        phaseStates.value.retrieval = 'running'
        break
      }

      case 'retrieval_result': {
        const rp = retrievalProgress.value
        if (rp) {
          rp.results = data.result_count as number
          rp.topScore = data.top_score as number
          rp.topPreview = data.top_preview as string || ''
        }
        currentDetail.value = `检索完成，找到 ${data.result_count} 条结果（最高相似度: ${(data.top_score as number || 0).toFixed(2)}）`
        recordPhaseTime(`retrieval_${data.step}`)
        break
      }

      case 'critique_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在评估检索质量...'
        phaseStartTimes.value['critique'] = Date.now()
        phaseStates.value.retrieval = 'complete'
        phaseStates.value.critique = 'running'
        break

      case 'critique_result': {
        const passed = data.passed as boolean
        critiqueResults.value.push({
          step: data.step as number,
          score: data.composite_score as number,
          relevance: data.relevance as number,
          completeness: data.completeness as number,
          passed,
          reasoning: data.reasoning as string || '',
          retrySuggestion: data.retry_suggestion as string || '',
        })
        currentDetail.value = `质量评估: ${(data.composite_score as number).toFixed(2)} 分 — ${passed ? '通过' : '不通过'}`
        recordPhaseTime('critique')
        phaseStates.value.critique = 'complete'
        phaseStates.value.synthesis = passed ? 'running' : 'waiting'
        break
      }

      case 'web_search_start':
        currentDetail.value = `正在联网搜索: ${(data.query as string || '').slice(0, 40)}...`
        webSearchResults.value = []
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
        break
      }

      case 'retry_triggered': {
        previousStep.value = currentStep.value
        const count = data.count as number
        currentDetail.value = `检索质量不达标，正在第 ${count} 次重试（改写查询）...`
        const lastCritique = critiqueResults.value[critiqueResults.value.length - 1]
        retryHistory.value.push({
          attempt: count,
          score: lastCritique?.score ?? 0,
          suggestion: lastCritique?.retrySuggestion ?? '',
        })
        phaseStates.value.critique = 'complete'
        phaseStates.value.retrieval = 'running'
        phaseStates.value.synthesis = 'waiting'
        break
      }

      case 'synthesis_start':
        previousStep.value = currentStep.value
        currentDetail.value = '正在聚合多源信息，生成研究报告...'
        phaseStartTimes.value['synthesis'] = Date.now()
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
        break

      case 'error':
        error.value = data.message as string || '发生未知错误'
        markCurrentPhaseError()
        isRunning.value = false
        break

      case 'cancelled':
        isCancelled.value = true
        isRunning.value = false
        markCurrentPhaseError()
        if (streamingReport.value && !report.value) {
          report.value = streamingReport.value
        }
        break
    }
  }

  function markCurrentPhaseError() {
    const phaseMap: Record<string, string> = {
      planning: 'decomposition',
      retrieving: 'retrieval',
      evaluating: 'critique',
      synthesizing: 'synthesis',
    }
    const phaseKey = phaseMap[previousStep.value]
    if (phaseKey) {
      phaseStates.value[phaseKey] = 'error'
    }
  }

  function setQuery(q: string) {
    query.value = q
  }

  function startResearch(tid: string) {
    taskId.value = tid
    isRunning.value = true
    isCancelled.value = false
    error.value = null
    report.value = ''
    streamingReport.value = ''
    sources.value = []
  }

  function setSources(s: Source[]) {
    sources.value = s
  }

  function setFinalReport(text: string, srcs: Source[]) {
    report.value = text
    sources.value = srcs
  }

  return {
    query, taskId, isRunning, isCancelled, error,
    report, streamingReport, sources,
    phaseStates, progressValue, currentDetail,
    researchPlan, critiqueResults, retrievalProgress, eventLog, retryHistory,
    startedAt, phaseDurations, phaseStartTimes, previousStep, webSearchResults,
    currentStep, phaseLabels,
    reset, handleEvent, setQuery, startResearch, setSources, setFinalReport,
  }
})
