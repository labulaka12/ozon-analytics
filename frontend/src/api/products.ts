import request from './request'
import type { Product, ProductDetail } from '@/types/product'

export function fetchProducts(storeId: number) {
  return request.get<Product[]>('/api/products', { params: { store_id: storeId } }).then(r => r.data)
}

export function fetchProductDetail(storeId: number, productId: number) {
  return request.get<ProductDetail>(`/api/products/${productId}`, { params: { store_id: storeId } }).then(r => r.data)
}
