const api=require('../../utils/api');const c=require('../../utils/cart')
Page({
 data:{location:{},detail:'',phone:'',remark:'',deliveryFee:'2.00',distance:'',total:'0.00',requestKey:''},
 onLoad(){this.setData({requestKey:`order-${Date.now()}-${Math.random().toString(36).slice(2,10)}`})},
 onShow(){this.refreshTotal()}, refreshTotal(){this.setData({total:(c.total()+2).toFixed(2)})},
 inputDetail(e){this.setData({detail:e.detail.value})},inputPhone(e){this.setData({phone:e.detail.value})},inputRemark(e){this.setData({remark:e.detail.value})},
 setLocation(location){this.setData({location});api.request(`/delivery/quote?latitude=${location.latitude}&longitude=${location.longitude}`).then(q=>this.setData({distance:q.distance_km,deliveryFee:Number(q.delivery_fee).toFixed(2),total:(c.total()+Number(q.delivery_fee)).toFixed(2)}))},
 chooseLocation(){wx.chooseLocation({success:r=>this.setLocation({name:r.name||r.address,latitude:r.latitude,longitude:r.longitude})})},
 useCurrentLocation(){wx.getLocation({type:'gcj02',success:r=>this.setLocation({name:'当前位置',latitude:r.latitude,longitude:r.longitude}),fail:()=>wx.showToast({title:'请授权定位',icon:'none'})})},
 submit(){const {location,detail,phone,remark,requestKey}=this.data;if(!location.latitude||!detail||!phone)return wx.showToast({title:'请完整填写收货信息',icon:'none'});const items=c.getCart().map(x=>({product_id:x.id,quantity:x.quantity}));api.request('/orders','POST',{items,address:{name:location.name,detail,latitude:location.latitude,longitude:location.longitude,phone},remark},{'X-Idempotency-Key':requestKey}).then(order=>api.request(`/orders/${order.id}/mock-payment-callback`,'POST').then(paid=>{c.saveCart([]);wx.redirectTo({url:`/pages/order-result/index?id=${paid.id}&no=${paid.order_no}`})})).catch(e=>wx.showToast({title:e.detail||'下单失败',icon:'none'}))}
})
