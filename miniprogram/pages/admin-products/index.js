const api=require('../../utils/api')
Page({
  data:{products:[],name:'',price:'',category:'粉面'},
  onShow(){this.load()},
  load(){api.request('/admin/products').then(products=>this.setData({products})).catch(e=>wx.showToast({title:e.detail||'需要商家权限',icon:'none'}))},
  inputName(e){this.setData({name:e.detail.value})},inputPrice(e){this.setData({price:e.detail.value})},inputCategory(e){this.setData({category:e.detail.value})},
  add(){const {name,price,category}=this.data;if(!name||!price)return wx.showToast({title:'请填写名称和售价',icon:'none'});api.request('/admin/products','POST',{name,price,category}).then(()=>{this.setData({name:'',price:''});this.load()}).catch(e=>wx.showToast({title:e.detail||'添加失败',icon:'none'}))},
  toggle(e){api.request(`/admin/products/${e.currentTarget.dataset.id}`,'PATCH',{enabled:!e.currentTarget.dataset.enabled}).then(()=>this.load()).catch(e=>wx.showToast({title:e.detail||'更新失败',icon:'none'}))}
})
