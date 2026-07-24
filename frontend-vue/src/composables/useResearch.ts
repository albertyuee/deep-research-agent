import { useResearchStore } from '@/stores/research'
import {
  submitResearch,
  fetchResearchTask,
  cancelResearch,
  researchStreamUrl,
} from '@/api/research'
import type { ResearchMode } from '@/api/research'

const delay = (milliseconds: number) => new Promise(resolve => setTimeout(resolve, milliseconds))

export function useResearch() {
  const store = useResearchStore()
  let eventSource: EventSource | null = null
  let connectionErrors = 0
  let checkingStatus = false
  let needsReplayReset = false

  function closeEventSource(source?: EventSource): void {
    if (source && source !== eventSource) return
    eventSource?.close()
    eventSource = null
  }

  async function fetchFinalResult(taskId: string): Promise<void> {
    const retryDelays = [0, 250, 750, 1500]
    for (const wait of retryDelays) {
      if (wait) await delay(wait)
      try {
        const task = await fetchResearchTask(taskId)
        if (task.result) {
          store.setFinalReport(
            task.result.report || store.report || store.streamingReport,
            task.result.sources || store.sources,
          )
          return
        }
      } catch {
        // Retry briefly: terminal SSE and result fetch can cross a network reconnect.
      }
    }

    if (store.streamingReport && !store.report) {
      store.setFinalReport(store.streamingReport, store.sources)
    } else {
      store.persist()
    }
  }

  async function inspectAfterConnectionError(source: EventSource, taskId: string): Promise<void> {
    if (checkingStatus || source !== eventSource) return
    checkingStatus = true
    try {
      const task = await fetchResearchTask(taskId)
      if (task.status === 'completed') {
        closeEventSource(source)
        await fetchFinalResult(taskId)
      } else if (task.status === 'failed') {
        closeEventSource(source)
        store.setFailure(task.error || '研究任务执行失败')
      } else if (task.status === 'cancelled') {
        closeEventSource(source)
        store.setCancelled('研究任务已取消')
      }
      // pending/running tasks are left open so EventSource can reconnect itself.
    } catch (error) {
      const message = error instanceof Error ? error.message : '无法查询研究任务状态'
      if (message.includes('404') || connectionErrors >= 3) {
        closeEventSource(source)
        store.setFailure(
          message.includes('404')
            ? '后端已重启或任务记录已失效，已保留当前研究内容，请重新发起任务。'
            : '研究进度连接持续中断，已保留当前研究内容，请检查后端服务。',
        )
      }
    } finally {
      checkingStatus = false
    }
  }

  function connectEventSource(taskId: string): void {
    closeEventSource()
    connectionErrors = 0
    needsReplayReset = false
    const source = new EventSource(researchStreamUrl(taskId))
    eventSource = source

    source.onopen = () => {
      if (source !== eventSource) return
      if (needsReplayReset) {
        // The backend stream replays from its buffer after reconnecting.
        // Clear event-derived data first to avoid duplicated report chunks.
        store.prepareForReplay()
        needsReplayReset = false
      }
      connectionErrors = 0
    }

    source.onmessage = (event: MessageEvent) => {
      if (source !== eventSource) return
      try {
        const payload = JSON.parse(event.data)
        const eventType = payload.event as string
        const eventData = (payload.data || {}) as Record<string, unknown>

        if (eventType === 'heartbeat') return
        if (eventType === 'timeout') {
          void inspectAfterConnectionError(source, taskId)
          return
        }

        store.handleEvent(eventType, eventData)
        if (eventType === 'done' || eventType === 'error' || eventType === 'cancelled') {
          closeEventSource(source)
          if (eventType === 'done') void fetchFinalResult(taskId)
        }
      } catch {
        // Ignore a malformed SSE frame; later valid events can still complete the task.
      }
    }

    source.onerror = () => {
      if (source !== eventSource) return
      connectionErrors += 1
      needsReplayReset = true
      void inspectAfterConnectionError(source, taskId)
    }
  }

  async function start(
    query: string,
    enableWebSearch: boolean = false,
    researchMode: ResearchMode = 'auto',
    maxHops: number = 3,
  ): Promise<void> {
    closeEventSource()
    store.reset()
    store.setQuery(query)

    try {
      const taskId = await submitResearch(query, enableWebSearch, researchMode, maxHops)
      store.startResearch(taskId, researchMode, maxHops)
      connectEventSource(taskId)
    } catch (error) {
      store.setFailure(error instanceof Error ? error.message : '连接后端失败')
    }
  }

  async function resume(): Promise<void> {
    const taskId = store.taskId
    if (!taskId || (!store.isRunning && (store.report || store.error || store.isCancelled))) return

    try {
      const task = await fetchResearchTask(taskId)
      if (task.status === 'completed') {
        if (task.result) {
          store.setFinalReport(
            task.result.report || store.report || store.streamingReport,
            task.result.sources || store.sources,
          )
        } else {
          await fetchFinalResult(taskId)
        }
      } else if (task.status === 'running' || task.status === 'pending') {
        store.prepareForReplay()
        connectEventSource(taskId)
      } else if (task.status === 'failed') {
        store.setFailure(task.error || '研究任务执行失败')
      } else if (task.status === 'cancelled') {
        store.setCancelled('研究任务已取消')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '无法恢复研究任务'
      store.setFailure(
        message.includes('404')
          ? '后端已重启或任务记录已失效，已保留当前研究内容，请重新发起任务。'
          : `恢复研究任务失败：${message}`,
      )
    }
  }

  async function stop(): Promise<void> {
    closeEventSource()
    if (store.taskId) {
      try {
        await cancelResearch(store.taskId)
      } catch {
        // Cancellation is best-effort; preserve all content already received.
      }
    }
    store.setCancelled()
  }

  function cleanup(): void {
    closeEventSource()
  }

  return { start, stop, resume, cleanup }
}
