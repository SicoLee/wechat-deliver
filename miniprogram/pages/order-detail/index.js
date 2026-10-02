const api=require('../../utils/api')
const STATUS_LABELS={PENDING_PAYMENT:'待支付',PAID:'待制作',MAKING:'制作中',READY_FOR_DELIVERY:'待配送',COMPLETED:'已完成'}
Page({data:{order:null},onLoad(q){api.request('/orders/'+q.id).then(order=>this.setData({order:{...order,statusLabel:STATUS_LABELS[order.status]||order.status}})).catch(e=>wx.showToast({title:e.detail||'加载订单失败',icon:'none'}))}})
