export interface Product {
  id: number
  store_id: number
  offer_id: string
  product_id: number
  sku: number | null
  name: string | null
  price: number | null
  status: string | null
}

export interface ProductDetail {
  id: number
  store_id: number
  offer_id: string
  product_id: number
  sku: number | null
  name: string | null
  category: string | null
  price: number | null
  old_price: number | null
  currency: string
  barcode: string | null
  status: string | null
}
