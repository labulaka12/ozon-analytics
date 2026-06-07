export interface OrderItem {
  posting_number: string
  order_type: string
  product_id: number
  offer_id: string | null
  product_name: string | null
  quantity: number
  price: number
  total_price: number
  status: string
  order_created_at: string | null
  shipped_at: string | null
  delivered_at: string | null
  commission: number
  payout: number
}

export interface OrderDetail {
  posting_number: string
  status: string
  order_type: string
  order_created_at: string | null
  shipped_at: string | null
  delivered_at: string | null
  items: {
    product_id: number
    offer_id: string | null
    product_name: string | null
    quantity: number
    price: number
    total_price: number
    commission: number
    payout: number
  }[]
}
