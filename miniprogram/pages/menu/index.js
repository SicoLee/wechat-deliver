const api = require('../../utils/api'); const cartApi = require('../../utils/cart')
Page({
  data:{products:[], cartCount:0, goodsTotal:'0.00'},
  onShow(){ this.refreshCart(); api.request('/products').then(products=>this.setData({products})).catch(()=>wx.showToast({title:'后端未启动',icon:'none'})) },
  refreshCart(){ const cart=cartApi.getCart(); this.setData({cartCount:cart.reduce((s,x)=>s+x.quantity,0),goodsTotal:cartApi.total(cart).toFixed(2)}) },
  add(e){ const product=this.data.products.find(x=>x.id===e.currentTarget.dataset.id); cartApi.add(product); this.refreshCart(); wx.showToast({title:'已加入'}) },
  goCart(){ wx.navigateTo({url:'/pages/cart/index'}) },
  goOrders(){ wx.navigateTo({url:'/pages/order-list/index'}) },
  goAdmin(){ wx.navigateTo({url:'/pages/admin-orders/index'}) }
})
