const api=require('../../utils/api');const app=getApp()
Page({
  data:{phone:'',orders:[],loaded:false,lastUpdated:''},
  onShow(){this.load();this.startPolling()},
  onHide(){this.stopPolling()},onUnload(){this.stopPolling()},
  onPullDownRefresh(){this.load(true)},
  inputPhone(e){this.setData({phone:e.detail.value})},
  bind(){api.request(`/auth/admin-bind?phone=${this.data.phone}`,'POST').then(()=>{wx.showToast({title:'绑定成功'});this.load()}).catch(e=>wx.showToast({title:e.detail||'绑定失败',icon:'none'}))},
  load(fromPullDown=false){api.request('/admin/orders').then(orders=>this.setData({orders,loaded:true,lastUpdated:`更新于 ${new Date().toLocaleTimeString()}`})).catch(()=>this.setData({loaded:true})).finally(()=>{if(fromPullDown)wx.stopPullDownRefresh()})},
  startPolling(){this.stopPolling();this.pollTimer=setInterval(()=>this.load(),10000)},
  stopPolling(){if(this.pollTimer){clearInterval(this.pollTimer);this.pollTimer=null}},
  products(){wx.navigateTo({url:'/pages/admin-products/index'})},
  detail(e){wx.navigateTo({url:'/pages/admin-order-detail/index?id='+e.currentTarget.dataset.id})}
})
