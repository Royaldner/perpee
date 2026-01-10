/**
 * API types matching backend schemas.
 */

// Product status enum matching backend
export type ProductStatus =
  | "active"
  | "paused"
  | "error"
  | "needs_attention"
  | "price_unavailable"
  | "archived"

// Alert type enum matching backend
export type AlertType =
  | "target_price"
  | "percent_drop"
  | "any_change"
  | "back_in_stock"

// WebSocket message types
export type MessageType =
  | "message"
  | "welcome"
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "response"
  | "error"

// Product types
export interface Product {
  id: number
  url: string
  store_domain: string
  name: string
  brand: string | null
  upc: string | null
  image_url: string | null
  current_price: number | null
  original_price: number | null
  currency: string
  in_stock: boolean
  status: ProductStatus
  consecutive_failures: number
  last_checked_at: string | null
  canonical_id: number | null
  created_at: string
  updated_at: string
}

export interface ProductListItem {
  id: number
  url: string
  store_domain: string
  name: string
  brand: string | null
  image_url: string | null
  current_price: number | null
  original_price: number | null
  in_stock: boolean
  status: ProductStatus
  last_checked_at: string | null
}

export interface ProductCreate {
  url: string
}

export interface ProductUpdate {
  status?: ProductStatus
  name?: string
}

export interface PriceHistoryItem {
  id: number
  price: number
  original_price: number | null
  in_stock: boolean
  scraped_at: string
}

export interface ProductPriceHistory {
  product: Product
  history: PriceHistoryItem[]
}

export interface ProductStats {
  total: number
  active: number
  paused: number
  needs_attention: number
  by_store: Record<string, number>
}

// Alert types
export interface Alert {
  id: number
  product_id: number
  alert_type: AlertType
  target_value: number | null
  min_change_threshold: number
  is_active: boolean
  is_triggered: boolean
  triggered_at: string | null
  created_at: string
  updated_at: string
}

export interface AlertListItem {
  id: number
  product_id: number
  alert_type: AlertType
  target_value: number | null
  is_active: boolean
  is_triggered: boolean
  triggered_at: string | null
}

export interface AlertWithProduct extends Alert {
  product_name: string
  product_url: string
  current_price: number | null
  store_domain: string
}

export interface AlertCreate {
  product_id: number
  alert_type: AlertType
  target_value?: number
  min_change_threshold?: number
}

export interface AlertUpdate {
  target_value?: number
  min_change_threshold?: number
  is_active?: boolean
}

// Schedule types
export interface Schedule {
  id: number
  product_id: number | null
  store_domain: string | null
  cron_expression: string
  is_active: boolean
  last_run_at: string | null
  next_run_at: string | null
  created_at: string
  updated_at: string
}

export interface ScheduleListItem {
  id: number
  product_id: number | null
  store_domain: string | null
  cron_expression: string
  is_active: boolean
  last_run_at: string | null
  next_run_at: string | null
}

export interface ScheduleWithDetails extends Schedule {
  product_name?: string
  store_name?: string
}

export interface ScheduleCreate {
  product_id?: number
  store_domain?: string
  cron_expression: string
}

export interface ScheduleUpdate {
  cron_expression?: string
  is_active?: boolean
}

// Store types
export interface Store {
  domain: string
  name: string
  is_whitelisted: boolean
  is_active: boolean
  rate_limit_rpm: number
  success_rate: number | null
  last_success_at: string | null
  created_at: string
  updated_at: string
}

export interface StoreListItem {
  domain: string
  name: string
  is_whitelisted: boolean
  is_active: boolean
}

export interface StoreHealth {
  domain: string
  name: string
  is_active: boolean
  product_count: number
  success_rate: number
  last_success_at: string | null
  health_status: "healthy" | "degraded" | "unhealthy"
}

export interface StoreStats {
  total: number
  active: number
  whitelisted: number
  avg_success_rate: number
}

// Chat/WebSocket types
export interface WebSocketMessage {
  type: MessageType
  data: Record<string, unknown>
  timestamp: string
}

export interface WelcomeData {
  message: string
  session_id: string | null
}

export interface ThinkingData {
  message: string
}

export interface ToolCallData {
  tool_name: string
  tool_args: Record<string, unknown>
}

export interface ToolResultData {
  tool_name: string
  success: boolean
  result: unknown
  error: string | null
}

export interface ResponseData {
  content: string
  tool_calls: ToolCallData[]
}

export interface ErrorData {
  message: string
  code: string | null
}

// Common types
export interface PaginationMeta {
  total: number
  page: number
  per_page: number
  pages: number
}

export interface PaginatedResponse<T> {
  items: T[]
  meta: PaginationMeta
}

export interface ErrorResponse {
  detail: string
  code?: string
}

export interface MessageResponse {
  message: string
}

// Health check types
export interface HealthCheck {
  status: "healthy" | "degraded" | "unhealthy"
  version: string
  database: boolean
  chromadb: boolean
  scheduler: boolean
}

export interface DashboardStats {
  products: ProductStats
  alerts: {
    total: number
    active: number
    triggered_today: number
  }
  recent_price_drops: {
    product_id: number
    product_name: string
    old_price: number
    new_price: number
    percent_change: number
    changed_at: string
  }[]
}
