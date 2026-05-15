import { useResearchStore } from '@/stores/research'
import { submitResearch, fetchResult, cancelResearch } from '@/api/research'

export function useResearch() {
  const store = useResearchStore()
  let eventSource: EventSource | null = null

  async function start(query: string): Promise<void> {
    store.reset()
    store.setQuery(query)

    try {
      const taskId = await submitResearch(query)
      store.startResearch(taskId)

      eventSource = new EventSource(`/api/v1/research/${taskId}/stream`)

      eventSource.onmessage = (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data)
          const eventType = payload.event
          const eventData = payload.data || {}
          store.handleEvent(eventType, eventData)

          if (eventType === 'done' || eventType === 'error' || eventType === 'cancelled') {
            eventSource?.close()
            eventSource = null

            if (eventType === 'done') {
              fetchFinalResult(taskId)
            }
          }
        } catch {
          // Skip malformed events
        }
      }

      eventSource.onerror = () => {
        if (eventSource) {
          store.error = 'SSE 连接中断'
          store.isRunning = false
          eventSource.close()
          eventSource = null
        }
      }
    } catch (e) {
      store.error = e instanceof Error ? e.message : '连接后端失败'
      store.isRunning = false
    }
  }

  async function stop(): Promise<void> {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    if (store.taskId) {
      try {
        await cancelResearch(store.taskId)
      } catch {
        // Best effort
      }
    }
    store.isRunning = false
    store.isCancelled = true
    if (store.streamingReport && !store.report) {
      store.report = store.streamingReport
    }
  }

  async function fetchFinalResult(taskId: string): Promise<void> {
    try {
      const result = await fetchResult(taskId)
      if (result) {
        store.setFinalReport(
          result.report || store.report,
          result.sources || store.sources,
        )
      }
    } catch {
      if (store.streamingReport && !store.report) {
        store.report = store.streamingReport
      }
    }
  }

  function cleanup(): void {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  return { start, stop, cleanup }
}
