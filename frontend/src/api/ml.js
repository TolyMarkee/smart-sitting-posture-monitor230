import request from './request'

export const mlApi = {
  // 聚类
  getCluster(userId, days = 7) {
    return request.get('/api/v1/ml/cluster-result', { params: { user_id: userId, days } })
  },
  trainCluster(userId, days = 7) {
    return request.post('/api/v1/ml/train-cluster', null, { params: { user_id: userId, days } })
  },
  // 健康评分
  getHealthScore({ head_angle, shoulder_diff, hunchback_score, body_tilt, round_shoulder }) {
    return request.post('/api/v1/ml/health-score', null, {
      params: { head_angle, shoulder_diff, hunchback_score, body_tilt, round_shoulder },
    })
  },
  // 预测
  getPrediction(userId, steps = 24, days = 7) {
    return request.get('/api/v1/ml/predict', { params: { user_id: userId, steps, days } })
  },
  // 综合报告
  getOverallReport(userId, days = 7) {
    return request.get('/api/v1/ml/overall-report', { params: { user_id: userId, days } })
  },
}
