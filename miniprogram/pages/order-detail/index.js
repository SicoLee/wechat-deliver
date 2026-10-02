const api=require('../../utils/api')
const STATUS_LABELS={PENDING_PAYMENT:'待支付',PAID:'待制作',MAKING:'制作中',READY_FOR_DELIVERY:'待配送',COMPLETED:'已完成'}
const STATUS_STEPS={PENDING_PAYMENT:0,PAID:1,MAKING:2,READY_FOR_DELIVERY:3,COMPLETED:4}
const STATUS_HINTS={PENDING_PAYMENT:'等待支付完成后，店家才能接单。',PAID:'订单已支付，店家将尽快开始制作。',MAKING:'店家正在制作，请稍等一会儿。',READY_FOR_DELIVERY:'餐品已做好，正等待配送。',COMPLETED:'本单已完成，感谢你的光临。'}
Page({data:{id:'',order:null,loadError:''},onLoad(query){this.setData({id:query.id});this.load()},load(){api.request('/orders/'+this.data.id).then(order=>this.setData({order:{...order,statusLabel:STATUS_LABELS[order.status]||order.status,statusStep:STATUS_STEPS[order.status]||0,statusHint:STATUS_HINTS[order.status]||'订单状态更新中。'},loadError:''})).catch(e=>this.setData({loadError:e.detail||'订单详情暂时无法加载，请稍后重试。'}))},retry(){this.load()}})
