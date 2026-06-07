/** 账户相关类型定义 */

export interface UserProfile {
  id: number
  email: string
  is_active: boolean
  email_verified: boolean
  role: string
  display_name: string | null
  created_at: string
}

export interface UpdateProfileRequest {
  display_name?: string
}

export interface UpdateEmailRequest {
  new_email: string
  password: string
}

export interface DeleteAccountRequest {
  password: string
  confirm: 'DELETE'
}
