const app = getApp()
function request(path, method = 'GET', data = {}) {
  return new Promise((resolve, reject) => wx.request({
    url: app.globalData.apiBase + path, method, data,
    header: { 'X-OpenID': app.globalData.demoOpenid },
    success: res => res.statusCode >= 200 && res.statusCode < 300 ? resolve(res.data) : reject(res.data),
    fail: reject
  }))
}
module.exports = { request }
