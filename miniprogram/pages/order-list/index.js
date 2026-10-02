const api=require('../../utils/api')
const STATUS_LABELS={PENDING_PAYMENT:'待支付',PAID:'待制作',MAKING:'制作中',READY_FOR_DELIVERY:'待配送',COMPLETED:'已完成'}
Page({data:{orders:[],loadError:''},onShow(){api.request('/orders/mine').then(orders=>this.setData({orders:orders.map(order=>({...order,statusLabel:STATUS_LABELS[order.status]||order.status})),loadError:''})).catch(()=>this.setData({loadError:'订单暂时无法加载，请稍后重试。'}))},detail(e){wx.navigateTo({url:'/pages/order-detail/index?id='+e.currentTarget.dataset.id})}})
