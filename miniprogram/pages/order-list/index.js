const api=require('../../utils/api')
Page({data:{orders:[]},onShow(){api.request('/orders/mine').then(orders=>this.setData({orders})).catch(()=>wx.showToast({title:'加载订单失败',icon:'none'}))}})
