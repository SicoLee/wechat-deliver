const api=require('../../utils/api')
Page({
  data:{products:[],name:'',price:'',category:'粉面',editingId:null,editName:'',editPrice:'',editCategory:'',loadError:''},
  onShow(){this.load()},
  load(){api.request('/admin/products').then(products=>this.setData({products,loadError:''})).catch(e=>this.setData({loadError:e.detail||'商品暂时无法加载，请稍后重试。'}))},
  retry(){this.load()},
  inputName(e){this.setData({name:e.detail.value})},inputPrice(e){this.setData({price:e.detail.value})},inputCategory(e){this.setData({category:e.detail.value})},
  add(){const {name,price,category}=this.data;if(!name||!price)return wx.showToast({title:'请填写名称和售价',icon:'none'});api.request('/admin/products','POST',{name,price,category}).then(()=>{this.setData({name:'',price:''});this.load()}).catch(e=>wx.showToast({title:e.detail||'添加失败',icon:'none'}))},
  startEdit(e){const product=this.data.products.find(item=>item.id===e.currentTarget.dataset.id);this.setData({editingId:product.id,editName:product.name,editPrice:product.price,editCategory:product.category})},
  inputEditName(e){this.setData({editName:e.detail.value})},inputEditPrice(e){this.setData({editPrice:e.detail.value})},inputEditCategory(e){this.setData({editCategory:e.detail.value})},
  cancelEdit(){this.setData({editingId:null})},
  saveEdit(){const {editingId,editName,editPrice,editCategory}=this.data;if(!editName||!editPrice||!editCategory)return wx.showToast({title:'请完整填写商品信息',icon:'none'});api.request(`/admin/products/${editingId}`,'PATCH',{name:editName,price:editPrice,category:editCategory}).then(()=>{this.setData({editingId:null});this.load()}).catch(e=>wx.showToast({title:e.detail||'保存失败',icon:'none'}))},
  toggle(e){api.request(`/admin/products/${e.currentTarget.dataset.id}`,'PATCH',{enabled:!e.currentTarget.dataset.enabled}).then(()=>this.load()).catch(e=>wx.showToast({title:e.detail||'更新失败',icon:'none'}))}
})
