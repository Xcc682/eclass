import { defineStore } from 'pinia'
import { ref } from 'vue'
import { interviewApi, type InterviewScenario, type InterviewMessage, type InterviewReport } from '@/api/interview'

export const useInterviewStore = defineStore('interview', () => {
  const scenarios = ref<InterviewScenario[]>([])
  const currentPracticeId = ref<string>('')
  const messages = ref<InterviewMessage[]>([])
  const report = ref<InterviewReport | null>(null)
  const isAiThinking = ref(false)

  async function fetchScenarios() {
    scenarios.value = await interviewApi.getScenarios()
  }

  async function startPractice(scenarioId: string) {
    const result = await interviewApi.startPractice(scenarioId)
    currentPracticeId.value = result.id
    messages.value = [{ id: '1', role: 'ai', content: result.first_question, round_number: 1, created_at: new Date().toISOString() }]
    return result
  }

  async function submitResponse(content: string) {
    if (!currentPracticeId.value) return
    isAiThinking.value = true

    // Add user message
    messages.value.push({
      id: Date.now().toString(),
      role: 'user',
      content,
      round_number: messages.value.filter(m => m.role === 'user').length + 1,
      created_at: new Date().toISOString()
    })

    try {
      const result = await interviewApi.submitResponse(currentPracticeId.value, content)

      // Add AI response
      messages.value.push({
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: result.question,
        ai_analysis: result.analysis,
        round_number: messages.value.filter(m => m.role === 'user').length,
        created_at: new Date().toISOString()
      })

      return result
    } finally {
      isAiThinking.value = false
    }
  }

  async function endPractice(): Promise<InterviewReport> {
    if (!currentPracticeId.value) throw new Error('No active practice')
    const result = await interviewApi.endPractice(currentPracticeId.value)
    report.value = result
    return result
  }

  async function loadReport(practiceId: string) {
    report.value = await interviewApi.getReport(practiceId)
  }

  function reset() {
    currentPracticeId.value = ''
    messages.value = []
    report.value = null
    isAiThinking.value = false
  }

  return {
    scenarios, currentPracticeId, messages, report, isAiThinking,
    fetchScenarios, startPractice, submitResponse, endPractice, loadReport, reset
  }
})
