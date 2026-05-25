import request from './request'

export const authApi = {
  // 认证
  login({ username, password }) {
    return request.post('/api/v1/auth/login', { username, password })
  },
  register({ username, email, password }) {
    return request.post('/api/v1/auth/register', { username, email, password })
  },
  // 个人中心
  getProfile() {
    return request.get('/api/v1/auth/profile')
  },
  updateProfile(data) {
    return request.put('/api/v1/auth/profile', data)
  },
  changePassword(old_password, new_password) {
    return request.put('/api/v1/auth/change-password', { old_password, new_password })
  },
  // 系统设置
  getSettings() {
    return request.get('/api/v1/auth/admin/settings')
  },
  updateSettings(params) {
    return request.put('/api/v1/auth/admin/settings', null, { params })
  },
  // 管理员
  adminListUsers(skip = 0, limit = 50) {
    return request.get('/api/v1/auth/admin/users', { params: { skip, limit } })
  },
  adminUpdateUser(userId, data) {
    return request.put(`/api/v1/auth/admin/users/${userId}`, data)
  },
  adminDeleteUser(userId) {
    return request.delete(`/api/v1/auth/admin/users/${userId}`)
  },
}
