const api=require('../../utils/api')
const STATUS_LABELS={PAID:'待制作',MAKING:'制作中',READY_FOR_DELIVERY:'待配送',COMPLETED:'已完成'}
const PRINT_LABELS={NOT_PRINTED:'待打印',SUCCESS:'已打印',FAILED:'打印失败'}
Page({
  data:{phone:'',orders:[],filteredOrders:[],filter:'ALL',loaded:false,lastUpdated:''},
  onShow(){this.load();this.startPolling()},
  onHide(){this.stopPolling()},onUnload(){this.stopPolling()},
  onPullDownRefresh(){this.load(true)},
  inputPhone(e){this.setData({phone:e.detail.value})},
  bind(){api.request(`/auth/admin-bind?phone=${this.data.phone}`,'POST').then(()=>{wx.showToast({title:'绑定成功'});this.load()}).catch(e=>wx.showToast({title:e.detail||'绑定失败',icon:'none'}))},
  load(fromPullDown=false){api.request('/admin/orders').then(orders=>this.setData({orders:orders.map(order=>({...order,statusLabel:STATUS_LABELS[order.status]||order.status,printLabel:PRINT_LABELS[order.print_status]||order.print_status})),loaded:true,lastUpdated:`更新于 ${new Date().toLocaleTimeString()}`},()=>this.applyFilter())).catch(()=>this.setData({loaded:true})).finally(()=>{if(fromPullDown)wx.stopPullDownRefresh()})},
  startPolling(){this.stopPolling();this.pollTimer=setInterval(()=>this.load(),10000)},
  stopPolling(){if(this.pollTimer){clearInterval(this.pollTimer);this.pollTimer=null}},
  setFilter(e){this.setData({filter:e.currentTarget.dataset.status},()=>this.applyFilter())},
  applyFilter(){const {orders,filter}=this.data;this.setData({filteredOrders:filter==='ALL'?orders:orders.filter(order=>order.status===filter)})},
  products(){wx.navigateTo({url:'/pages/admin-products/index'})},
  detail(e){wx.navigateTo({url:'/pages/admin-order-detail/index?id='+e.currentTarget.dataset.id})}
})
