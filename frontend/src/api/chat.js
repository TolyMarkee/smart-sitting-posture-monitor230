import request from './request'

export const chatApi = {
  sendMessage(message, history = [], userId = null) {
    return request.post('/api/v1/chat/message', { message, history, user_id: userId })
  },
  getHistory(userId, limit = 200) {
    return request.get('/api/v1/chat/history', { params: { user_id: userId, limit } })
  },
  clearHistory(userId) {
    return request.delete('/api/v1/chat/history', { params: { user_id: userId } })
  },
}
