import api from './client'

const BASE = '/api/v1/admin'

export interface DashboardStats {
  total_users: number; total_customers: number; total_orders: number
  total_tickets: number; pending_tickets: number; open_tickets: number
  total_shipments: number; pending_refunds: number
  kb_chunks: number; kb_initialized: boolean
  active_sessions: number; total_conversations: number
}

export interface UserItem {
  id: string; email: string; username: string; display_name: string | null
  role: string; is_active: boolean; is_verified: boolean
  company: string | null; created_at: string | null
}

export interface CustomerItem {
  id: string; user_id: string | null; display_name: string; email: string
  company: string | null; phone: string | null; account_status: string
  loyalty_tier: string; loyalty_points: number; order_count: number
  created_at: string | null
}

export interface OrderItem {
  id: string; order_number: string; customer_id: string
  status: string; total: number; created_at: string
}

export interface ShipmentItem {
  id: string; tracking_number: string; courier: string; customer_id: string | null
  status: string; current_location: string | null
  estimated_delivery: string | null; created_at: string | null
}

export interface TicketItem {
  id: string; ticket_number: string; customer_id: string; subject: string
  status: string; priority: string; category: string | null
  assigned_to: string | null; comment_count: number; created_at: string
}

export interface RefundItem {
  id: string; order_number: string; customer_id: string; reason: string
  status: string; refund_amount: number; rma_number: string; created_at: string
}

export interface KBFile {
  name: string; size_bytes: number; last_modified: string
}

export interface SessionItem {
  session_id: string; message_count: number
  created_at?: string; last_active?: string
}

export interface HealthCheck {
  overall: string
  checks: Record<string, { status: string; detail: string }>
}

export const adminApi = {
  getDashboard: () => api.get<DashboardStats>(`${BASE}/dashboard`).then(r => r.data),

  listUsers: (skip = 0, limit = 50, search?: string) =>
    api.get<{ users: UserItem[]; total: number }>(`${BASE}/users`, { params: { skip, limit, search } }).then(r => r.data),

  updateUserRole: (userId: string, role: string) =>
    api.patch(`${BASE}/users/${userId}/role`, { role }).then(r => r.data),

  listCustomers: (skip = 0, limit = 50, search?: string) =>
    api.get<{ customers: CustomerItem[]; total: number }>(`${BASE}/customers`, { params: { skip, limit, search } }).then(r => r.data),

  getCustomerDetail: (id: string) =>
    api.get<{ customer: any; orders: any[]; tickets: any[]; shipments: any[] }>(`${BASE}/customers/${id}`).then(r => r.data),

  listOrders: (skip = 0, limit = 50, status?: string, search?: string) =>
    api.get<{ orders: OrderItem[]; total: number }>(`${BASE}/orders`, { params: { skip, limit, status, search } }).then(r => r.data),

  getOrderDetail: (orderNumber: string) =>
    api.get<any>(`${BASE}/orders/${orderNumber}`).then(r => r.data),

  updateOrderStatus: (orderNumber: string, status: string, notes?: string) =>
    api.patch(`${BASE}/orders/${orderNumber}/status`, { status, notes }).then(r => r.data),

  listTickets: (skip = 0, limit = 50, status?: string, search?: string) =>
    api.get<{ tickets: TicketItem[]; total: number }>(`${BASE}/tickets`, { params: { skip, limit, status, search } }).then(r => r.data),

  getTicketDetail: (id: string) =>
    api.get<any>(`${BASE}/tickets/${id}`).then(r => r.data),

  updateTicket: (id: string, data: { status?: string; assigned_to?: string; note?: string }) =>
    api.patch(`${BASE}/tickets/${id}`, data).then(r => r.data),

  addTicketComment: (id: string, body: string, isInternal = true) =>
    api.post(`${BASE}/tickets/${id}/comments`, { body, is_internal: isInternal }).then(r => r.data),

  listRefunds: (skip = 0, limit = 50, status?: string) =>
    api.get<{ refunds: RefundItem[]; total: number }>(`${BASE}/refunds`, { params: { skip, limit, status } }).then(r => r.data),

  approveRefund: (id: string, notes?: string) =>
    api.post(`${BASE}/refunds/${id}/approve`, { notes }).then(r => r.data),

  rejectRefund: (id: string, notes?: string) =>
    api.post(`${BASE}/refunds/${id}/reject`, { notes }).then(r => r.data),

  listShipments: (skip = 0, limit = 50, status?: string) =>
    api.get<{ shipments: ShipmentItem[]; total: number }>(`${BASE}/shipments`, { params: { skip, limit, status } }).then(r => r.data),

  createShipment: (data: any) =>
    api.post(`${BASE}/shipments`, data).then(r => r.data),

  updateShipment: (trackingNumber: string, data: any) =>
    api.patch(`${BASE}/shipments/${trackingNumber}`, data).then(r => r.data),

  listKnowledgeBase: () =>
    api.get<{ files: KBFile[]; total: number }>(`${BASE}/knowledge-base`).then(r => r.data),

  uploadKnowledgeBase: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`${BASE}/knowledge-base/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  deleteKnowledgeBaseFile: (filename: string) =>
    api.delete(`${BASE}/knowledge-base/${encodeURIComponent(filename)}`).then(r => r.data),

  rebuildKnowledgeBase: () =>
    api.post(`${BASE}/knowledge-base/rebuild`).then(r => r.data),

  getAnalyticsOverview: () =>
    api.get<{ total_orders: number; total_tickets: number; resolved_tickets: number; resolution_rate: number; active_sessions: number }>(`${BASE}/analytics/overview`).then(r => r.data),

  listSessions: (skip = 0, limit = 50) =>
    api.get<{ sessions: SessionItem[]; total: number }>(`${BASE}/sessions`, { params: { skip, limit } }).then(r => r.data),

  getSessionMessages: (sessionId: string) =>
    api.get<{ session_id: string; messages: any[]; summary: string }>(`${BASE}/sessions/${sessionId}/messages`).then(r => r.data),

  getHealth: () =>
    api.get<HealthCheck>(`${BASE}/health`).then(r => r.data),
}
