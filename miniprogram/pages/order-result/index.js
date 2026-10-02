Page({data:{id:'',no:''},onLoad(q){this.setData({id:q.id,no:q.no})},detail(){wx.redirectTo({url:'/pages/order-detail/index?id='+this.data.id})},back(){wx.reLaunch({url:'/pages/menu/index'})}})
