App({
  globalData: {
    // 真机调试请换成已备案 HTTPS 域名；开发者工具中可先勾选“不校验合法域名”。
    apiBase: 'http://127.0.0.1:8000/api',
    demoOpenid: 'demo-customer-openid'
  },
  onLaunch() {
    if (!wx.getStorageSync('cart')) wx.setStorageSync('cart', [])
  }
})
