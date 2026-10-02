function getCart() { return wx.getStorageSync('cart') || [] }
function saveCart(cart) { wx.setStorageSync('cart', cart) }
function add(product) {
  const cart = getCart(); const line = cart.find(x => x.id === product.id)
  if (line) line.quantity += 1; else cart.push({...product, quantity: 1})
  saveCart(cart)
}
function total(cart = getCart()) { return cart.reduce((sum, x) => sum + Number(x.price) * x.quantity, 0) }
module.exports = {getCart, saveCart, add, total}
