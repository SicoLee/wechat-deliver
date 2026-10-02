const api=require('../../utils/api')
const STATUS_LABELS={PENDING_PAYMENT:'待支付',PAID:'待制作',MAKING:'制作中',READY_FOR_DELIVERY:'待配送',COMPLETED:'已完成'}
Page({data:{order:null,loadError:''},onLoad(q){api.request('/orders/'+q.id).then(order=>this.setData({order:{...order,statusLabel:STATUS_LABELS[order.status]||order.status},loadError:''})).catch(e=>this.setData({loadError:e.detail||'订单详情暂时无法加载，请稍后重试。'}))}})
