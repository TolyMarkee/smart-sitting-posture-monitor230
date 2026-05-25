import request from './request'

export const dataApi = {
  getLatest(userId) {
    return request.get('/api/v1/data/latest', { params: { user_id: userId } })
  },
  getHistory(userId, start = null, end = null, limit = 500) {
    return request.get('/api/v1/data/history', {
      params: { user_id: userId, start, end, limit },
    })
  },
  getDailySummary(userId, startDate = null, endDate = null) {
    return request.get('/api/v1/data/daily-summary', {
      params: { user_id: userId, start_date: startDate, end_date: endDate },
    })
  },
  generateDemo(userId, days = 3) {
    return request.post('/api/v1/data/generate-demo', null, { params: { user_id: userId, days } })
  },
  getWeather() {
    return request.get('/api/v1/data/weather')
  },
}
