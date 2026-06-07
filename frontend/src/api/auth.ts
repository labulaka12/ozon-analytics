import request from './request'

export interface LoginData {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserInfo
}

export interface UserInfo {
  id: number
  email: string
  is_active: boolean
  email_verified: boolean
  role: string
  display_name: string | null
  created_at: string
}

export function login(data: LoginData) {
  return request.post<TokenResponse>('/api/auth/login', data).then(r => r.data)
}

export function register(data: RegisterData) {
  return request.post<TokenResponse>('/api/auth/register', data).then(r => r.data)
}

export function fetchUserInfo() {
  return request.get<UserInfo>('/api/auth/me').then(r => r.data)
}
