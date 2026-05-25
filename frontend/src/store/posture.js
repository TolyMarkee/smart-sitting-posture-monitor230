import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dataApi } from '../api/data'

export const usePostureStore = defineStore('posture', () => {
  const latest = ref(null)          // 最新一条记录
  const history = ref([])           // 历史记录列表
  const dailyStats = ref([])        // 每日统计
  const loading = ref(false)

  async function fetchLatest(userId) {
    const { data } = await dataApi.getLatest(userId)
    if (data.record) {
      latest.value = data.record
    }
    return data
  }

  async function fetchHistory(userId, start = null, end = null) {
    loading.value = true
    try {
      const { data } = await dataApi.getHistory(userId, start, end)
      history.value = data.records || []
    } finally {
      loading.value = false
    }
  }

  async function fetchDailySummary(userId, startDate = null, endDate = null) {
    const { data } = await dataApi.getDailySummary(userId, startDate, endDate)
    dailyStats.value = data.stats || []
    return data
  }

  return { latest, history, dailyStats, loading, fetchLatest, fetchHistory, fetchDailySummary }
})
