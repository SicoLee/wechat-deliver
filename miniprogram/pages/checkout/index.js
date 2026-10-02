const api = require('../../utils/api')
const cart = require('../../utils/cart')

Page({
  data: {
    location: {}, detail: '', phone: '', remark: '', deliveryFee: '--', distance: '',
    distanceSource: '', total: '0.00', requestKey: '', quoteReady: false,
    quoteError: '', submitting: false
  },
  onLoad() {
    this.setData({ requestKey: `order-${Date.now()}-${Math.random().toString(36).slice(2, 10)}` })
  },
  onShow() { this.refreshTotal() },
  refreshTotal() { this.setData({ total: (cart.total() + 2).toFixed(2) }) },
  inputDetail(event) { this.setData({ detail: event.detail.value }) },
  inputPhone(event) { this.setData({ phone: event.detail.value }) },
  inputRemark(event) { this.setData({ remark: event.detail.value }) },
  setLocation(location) {
    this.setData({ location, quoteReady: false, quoteError: '', distance: '', distanceSource: '', deliveryFee: '--', total: cart.total().toFixed(2) })
    api.request(`/delivery/quote?latitude=${location.latitude}&longitude=${location.longitude}`)
      .then((quote) => this.setData({ distance: quote.distance_km, distanceSource: quote.distance_source, deliveryFee: Number(quote.delivery_fee).toFixed(2), total: (cart.total() + Number(quote.delivery_fee)).toFixed(2), quoteReady: true }))
      .catch((error) => this.setData({ quoteError: error.detail || '暂时无法计算配送费，请稍后重试' }))
  },
  chooseLocation() {
    wx.chooseLocation({ success: (result) => this.setLocation({ name: result.name || result.address, latitude: result.latitude, longitude: result.longitude }), fail: () => wx.showToast({ title: '未选择地图地点', icon: 'none' }) })
  },
  useCurrentLocation() {
    wx.getLocation({ type: 'gcj02', success: (result) => this.setLocation({ name: '当前位置', latitude: result.latitude, longitude: result.longitude }), fail: () => wx.showToast({ title: '请授权定位', icon: 'none' }) })
  },
  submit() {
    const { location, detail, phone, remark, requestKey, quoteReady, submitting } = this.data
    if (submitting) return
    if (!location.latitude) return wx.showToast({ title: '请先选择收货地点', icon: 'none' })
    if (!detail.trim()) return wx.showToast({ title: '请填写详细门牌号', icon: 'none' })
    if (!/^1\d{10}$/.test(phone)) return wx.showToast({ title: '请输入正确的 11 位手机号', icon: 'none' })
    if (!quoteReady) return wx.showToast({ title: '请先等待配送费计算完成', icon: 'none' })
    this.setData({ submitting: true })
    const items = cart.getCart().map((item) => ({ product_id: item.id, quantity: item.quantity }))
    const address = { name: location.name, detail: detail.trim(), latitude: location.latitude, longitude: location.longitude, phone }
    api.request('/orders', 'POST', { items, address, remark: remark.trim() }, { 'X-Idempotency-Key': requestKey })
      .then((order) => api.request(`/orders/${order.id}/mock-payment-callback`, 'POST'))
      .then((paid) => {
        cart.saveCart([])
        wx.redirectTo({ url: `/pages/order-result/index?id=${paid.id}&no=${paid.order_no}` })
      })
      .catch((error) => {
        this.setData({ submitting: false })
        wx.showToast({ title: error.detail || '下单失败', icon: 'none' })
      })
  }
})
