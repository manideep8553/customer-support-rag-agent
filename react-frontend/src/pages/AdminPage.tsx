import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'
import { adminApi, type DashboardStats, type CustomerItem, type OrderItem, type ShipmentItem, type TicketItem, type RefundItem, type KBFile, type SessionItem, type HealthCheck, type UserItem } from '@/api/adminClient'
import { MessageEntry } from '@/api/client'

type Tab = 'dashboard' | 'customers' | 'orders' | 'shipments' | 'tickets' | 'refunds' | 'knowledge' | 'analytics' | 'conversations' | 'users' | 'health'

const tabs: { id: Tab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'customers', label: 'Customers' },
  { id: 'orders', label: 'Orders' },
  { id: 'shipments', label: 'Shipments' },
  { id: 'tickets', label: 'Tickets' },
  { id: 'refunds', label: 'Refunds' },
  { id: 'knowledge', label: 'Knowledge Base' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'users', label: 'Users' },
  { id: 'health', label: 'Health' },
]

function StatusBadge({ status }: { status: string }) {
  const color: Record<string, string> = {
    healthy: 'bg-green-500/20 text-green-600',
    unhealthy: 'bg-red-500/20 text-red-600',
    degraded: 'bg-yellow-500/20 text-yellow-600',
    active: 'bg-green-500/20 text-green-600',
    inactive: 'bg-gray-500/20 text-gray-600',
    delivered: 'bg-green-500/20 text-green-600',
    shipped: 'bg-blue-500/20 text-blue-600',
    pending: 'bg-yellow-500/20 text-yellow-600',
    confirmed: 'bg-blue-500/20 text-blue-600',
    cancelled: 'bg-red-500/20 text-red-600',
    refunded: 'bg-purple-500/20 text-purple-600',
    resolved: 'bg-green-500/20 text-green-600',
    closed: 'bg-gray-500/20 text-gray-600',
    open: 'bg-blue-500/20 text-blue-600',
    in_progress: 'bg-yellow-500/20 text-yellow-600',
    escalated: 'bg-red-500/20 text-red-600',
    pre_transit: 'bg-gray-500/20 text-gray-600',
    in_transit: 'bg-blue-500/20 text-blue-600',
    out_for_delivery: 'bg-yellow-500/20 text-yellow-600',
    requested: 'bg-yellow-500/20 text-yellow-600',
    approved: 'bg-green-500/20 text-green-600',
    rejected: 'bg-red-500/20 text-red-600',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color[status] || 'bg-gray-500/20 text-gray-600'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

function Spinner() {
  return <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
}

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-background border rounded-lg shadow-lg max-w-2xl w-full max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="p-1 hover:bg-secondary rounded">&times;</button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  )
}

/* ───────── Dashboard Tab ───────── */
function DashboardTab() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => { adminApi.getDashboard().then(setStats) }, [])

  if (!stats) return <div className="flex justify-center py-20"><Spinner /></div>

  const cards = [
    { label: 'Users', value: stats.total_users },
    { label: 'Customers', value: stats.total_customers },
    { label: 'Orders', value: stats.total_orders },
    { label: 'Tickets', value: stats.total_tickets },
    { label: 'Open Tickets', value: stats.open_tickets },
    { label: 'Shipments', value: stats.total_shipments },
    { label: 'Pending Refunds', value: stats.pending_refunds },
    { label: 'KB Chunks', value: stats.kb_chunks },
    { label: 'Active Sessions', value: stats.active_sessions },
  ]
  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Dashboard Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {cards.map(c => (
          <div key={c.label} className="border rounded-lg p-4 bg-card">
            <div className="text-2xl font-bold">{c.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{c.label}</div>
          </div>
        ))}
      </div>
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold mb-2">Knowledge Base</h3>
          <p className="text-sm">Initialized: {stats.kb_initialized ? 'Yes' : 'No'}</p>
          <p className="text-sm">Chunks: {stats.kb_chunks}</p>
        </div>
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold mb-2">Sessions</h3>
          <p className="text-sm">Active: {stats.active_sessions}</p>
          <p className="text-sm">Total: {stats.total_conversations}</p>
        </div>
      </div>
    </div>
  )
}

/* ───────── Customers Tab ───────── */
function CustomersTab() {
  const [customers, setCustomers] = useState<CustomerItem[]>([])
  const [search, setSearch] = useState('')
  const [detail, setDetail] = useState<any>(null)

  const load = useCallback(() => {
    adminApi.listCustomers(0, 100, search || undefined).then(r => setCustomers(r.customers))
  }, [search])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold flex-1">Customers</h2>
        <input className="border rounded px-3 py-1.5 text-sm bg-background w-64" placeholder="Search name, email, company..." value={search} onChange={e => setSearch(e.target.value)} />
        <button onClick={load} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Refresh</button>
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{['Name', 'Email', 'Company', 'Tier', 'Orders', 'Status'].map(h => <th key={h} className="text-left p-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {customers.map(c => (
              <tr key={c.id} className="border-t hover:bg-muted/30 cursor-pointer" onClick={() => adminApi.getCustomerDetail(c.id).then(setDetail)}>
                <td className="p-2">{c.display_name}</td>
                <td className="p-2 text-muted-foreground">{c.email}</td>
                <td className="p-2">{c.company || '-'}</td>
                <td className="p-2"><StatusBadge status={c.loyalty_tier} /></td>
                <td className="p-2">{c.order_count}</td>
                <td className="p-2"><StatusBadge status={c.account_status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal open={!!detail} onClose={() => setDetail(null)} title={`Customer: ${detail?.customer?.display_name || ''}`}>
        {detail && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-muted-foreground">Email:</span> {detail.customer.email}</div>
              <div><span className="text-muted-foreground">Company:</span> {detail.customer.company || '-'}</div>
              <div><span className="text-muted-foreground">Phone:</span> {detail.customer.phone || '-'}</div>
              <div><span className="text-muted-foreground">Total Spent:</span> ${detail.customer.total_spent?.toFixed(2)}</div>
              <div><span className="text-muted-foreground">Points:</span> {detail.customer.loyalty_points}</div>
              <div><span className="text-muted-foreground">Status:</span> <StatusBadge status={detail.customer.account_status} /></div>
            </div>
            {detail.orders.length > 0 && (
              <div><h3 className="font-semibold mb-2">Orders</h3>
                {detail.orders.map((o: any) => <div key={o.order_number} className="text-sm py-1">{o.order_number} <StatusBadge status={o.status} /> ${o.total}</div>)}
              </div>
            )}
            {detail.tickets.length > 0 && (
              <div><h3 className="font-semibold mb-2">Tickets</h3>
                {detail.tickets.map((t: any) => <div key={t.ticket_number} className="text-sm py-1">{t.ticket_number} - {t.subject} <StatusBadge status={t.status} /></div>)}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ───────── Orders Tab ───────── */
function OrdersTab() {
  const [orders, setOrders] = useState<OrderItem[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [detail, setDetail] = useState<any>(null)
  const [statusForm, setStatusForm] = useState('')
  const [notesForm, setNotesForm] = useState('')
  const [detailOrder, setDetailOrder] = useState('')

  useEffect(() => { adminApi.listOrders(0, 100, statusFilter || undefined).then(r => setOrders(r.orders)) }, [statusFilter])

  const openDetail = async (on: string) => {
    setDetailOrder(on)
    const d = await adminApi.getOrderDetail(on)
    setDetail(d)
    setStatusForm(d.status)
    setNotesForm('')
  }

  const updateStatus = async () => {
    await adminApi.updateOrderStatus(detailOrder, statusForm, notesForm || undefined)
    openDetail(detailOrder)
    adminApi.listOrders(0, 100, statusFilter || undefined).then(r => setOrders(r.orders))
  }

  const statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
  return (
    <div>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <h2 className="text-xl font-bold">Orders</h2>
        <select className="border rounded px-2 py-1.5 text-sm bg-background" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {statuses.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{['Order #', 'Status', 'Total', 'Date'].map(h => <th key={h} className="text-left p-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {orders.map(o => (
              <tr key={o.id} className="border-t hover:bg-muted/30 cursor-pointer" onClick={() => openDetail(o.order_number)}>
                <td className="p-2 font-mono text-xs">{o.order_number}</td>
                <td className="p-2"><StatusBadge status={o.status} /></td>
                <td className="p-2">${o.total.toFixed(2)}</td>
                <td className="p-2 text-muted-foreground">{new Date(o.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal open={!!detail} onClose={() => setDetail(null)} title={`Order: ${detail?.order_number || ''}`}>
        {detail && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-muted-foreground">Status:</span> <StatusBadge status={detail.status} /></div>
              <div><span className="text-muted-foreground">Payment:</span> {detail.payment_status || '-'}</div>
              <div><span className="text-muted-foreground">Total:</span> ${detail.total?.toFixed(2)}</div>
              <div><span className="text-muted-foreground">Shipping:</span> {detail.shipping_method || '-'}</div>
              <div><span className="text-muted-foreground">Tracking:</span> {detail.tracking_number || '-'}</div>
              <div><span className="text-muted-foreground">Carrier:</span> {detail.carrier || '-'}</div>
            </div>
            <div className="border-t pt-3">
              <h3 className="font-semibold mb-2">Update Status</h3>
              <div className="flex gap-2">
                <select className="border rounded px-2 py-1.5 text-sm bg-background flex-1" value={statusForm} onChange={e => setStatusForm(e.target.value)}>
                  {statuses.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <input className="border rounded px-2 py-1.5 text-sm bg-background flex-1" placeholder="Notes" value={notesForm} onChange={e => setNotesForm(e.target.value)} />
                <button onClick={updateStatus} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Update</button>
              </div>
            </div>
            {detail.status_logs?.length > 0 && (
              <div className="border-t pt-3">
                <h3 className="font-semibold mb-2">Status History</h3>
                {detail.status_logs.map((l: any, i: number) => (
                  <div key={i} className="text-xs text-muted-foreground py-1 border-b border-border/50">
                    {l.from_status} → {l.to_status} {l.notes ? `: ${l.notes}` : ''} <span className="float-right">{new Date(l.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ───────── Shipments Tab ───────── */
function ShipmentsTab() {
  const [shipments, setShipments] = useState<ShipmentItem[]>([])
  const [filter, setFilter] = useState('')

  const load = useCallback(() => { adminApi.listShipments(0, 100, filter || undefined).then(r => setShipments(r.shipments)) }, [filter])
  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold flex-1">Shipments</h2>
        <select className="border rounded px-2 py-1.5 text-sm bg-background" value={filter} onChange={e => setFilter(e.target.value)}>
          <option value="">All</option>
          {['pre_transit', 'in_transit', 'out_for_delivery', 'delivered', 'exception'].map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
        </select>
        <button onClick={load} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Refresh</button>
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{['Tracking #', 'Courier', 'Status', 'Location', 'Est. Delivery'].map(h => <th key={h} className="text-left p-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {shipments.map(s => (
              <tr key={s.id} className="border-t hover:bg-muted/30">
                <td className="p-2 font-mono text-xs">{s.tracking_number}</td>
                <td className="p-2">{s.courier}</td>
                <td className="p-2"><StatusBadge status={s.status} /></td>
                <td className="p-2 text-muted-foreground">{s.current_location || '-'}</td>
                <td className="p-2 text-muted-foreground">{s.estimated_delivery ? new Date(s.estimated_delivery).toLocaleDateString() : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ───────── Tickets Tab ───────── */
function TicketsTab() {
  const [tickets, setTickets] = useState<TicketItem[]>([])
  const [filter, setFilter] = useState('')
  const [detail, setDetail] = useState<any>(null)
  const [commentText, setCommentText] = useState('')
  const [isInternal, setIsInternal] = useState(true)

  const load = useCallback(() => { adminApi.listTickets(0, 100, filter || undefined).then(r => setTickets(r.tickets)) }, [filter])
  useEffect(() => { load() }, [load])

  const openDetail = async (id: string) => {
    const d = await adminApi.getTicketDetail(id)
    setDetail(d)
    setCommentText('')
  }

  const addComment = async () => {
    if (!commentText.trim() || !detail) return
    await adminApi.addTicketComment(detail.id, commentText, isInternal)
    setCommentText('')
    openDetail(detail.id)
  }

  const updateStatus = async (status: string) => {
    await adminApi.updateTicket(detail.id, { status })
    openDetail(detail.id)
    load()
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold flex-1">Tickets</h2>
        <select className="border rounded px-2 py-1.5 text-sm bg-background" value={filter} onChange={e => setFilter(e.target.value)}>
          <option value="">All</option>
          {['open', 'in_progress', 'waiting_customer', 'escalated', 'resolved', 'closed'].map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
        </select>
        <button onClick={load} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Refresh</button>
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{['Ticket #', 'Subject', 'Status', 'Priority', 'Assigned', 'Comments'].map(h => <th key={h} className="text-left p-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {tickets.map(t => (
              <tr key={t.id} className="border-t hover:bg-muted/30 cursor-pointer" onClick={() => openDetail(t.id)}>
                <td className="p-2 font-mono text-xs">{t.ticket_number}</td>
                <td className="p-2 max-w-[200px] truncate">{t.subject}</td>
                <td className="p-2"><StatusBadge status={t.status} /></td>
                <td className="p-2">{t.priority}</td>
                <td className="p-2 text-muted-foreground">{t.assigned_to || 'Unassigned'}</td>
                <td className="p-2">{t.comment_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal open={!!detail} onClose={() => setDetail(null)} title={`Ticket: ${detail?.ticket_number || ''}`}>
        {detail && (
          <div className="space-y-4">
            <div className="text-sm">
              <p><span className="text-muted-foreground">Subject:</span> {detail.subject}</p>
              <p><span className="text-muted-foreground">Description:</span> {detail.description}</p>
              <div className="flex gap-2 mt-2">
                <StatusBadge status={detail.status} />
                <span className="text-xs text-muted-foreground">{detail.priority} priority</span>
                <span className="text-xs text-muted-foreground">Assigned: {detail.assigned_to || 'Unassigned'}</span>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              {['open', 'in_progress', 'resolved', 'closed'].map(s => (
                <button key={s} onClick={() => updateStatus(s)} disabled={detail.status === s}
                  className="px-2 py-1 text-xs rounded border hover:bg-secondary disabled:opacity-40">{s.replace(/_/g, ' ')}</button>
              ))}
            </div>
            <div className="border-t pt-3">
              <h3 className="font-semibold mb-2">Comments ({detail.comments?.length || 0})</h3>
              <div className="max-h-60 overflow-y-auto space-y-2 mb-3">
                {(detail.comments || []).map((c: any) => (
                  <div key={c.id} className={`text-sm p-2 rounded ${c.is_internal ? 'bg-yellow-500/10 border border-yellow-500/20' : 'bg-muted/30'}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-xs">{c.author}</span>
                      {c.is_internal && <span className="text-[10px] text-yellow-600 bg-yellow-500/20 px-1 rounded">Internal</span>}
                      <span className="text-[10px] text-muted-foreground ml-auto">{new Date(c.created_at).toLocaleString()}</span>
                    </div>
                    <div className="whitespace-pre-wrap">{c.body}</div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <textarea className="border rounded p-2 text-sm bg-background flex-1 min-h-[60px]" placeholder="Add comment..." value={commentText} onChange={e => setCommentText(e.target.value)} />
              </div>
              <div className="flex items-center gap-2 mt-2">
                <label className="flex items-center gap-1 text-sm"><input type="checkbox" checked={isInternal} onChange={e => setIsInternal(e.target.checked)} /> Internal</label>
                <button onClick={addComment} disabled={!commentText.trim()} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm ml-auto">Send</button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

/* ───────── Refunds Tab ───────── */
function RefundsTab() {
  const [refunds, setRefunds] = useState<RefundItem[]>([])
  const [filter, setFilter] = useState('')
  const [actionNotes, setActionNotes] = useState('')

  const load = useCallback(() => { adminApi.listRefunds(0, 100, filter || undefined).then(r => setRefunds(r.refunds)) }, [filter])
  useEffect(() => { load() }, [load])

  const approve = async (id: string) => {
    await adminApi.approveRefund(id, actionNotes || undefined)
    setActionNotes('')
    load()
  }
  const reject = async (id: string) => {
    await adminApi.rejectRefund(id, actionNotes || undefined)
    setActionNotes('')
    load()
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold flex-1">Refund Requests</h2>
        <select className="border rounded px-2 py-1.5 text-sm bg-background" value={filter} onChange={e => setFilter(e.target.value)}>
          <option value="">All</option>
          {['requested', 'approved', 'rejected', 'label_sent', 'item_received', 'refund_processed'].map(s => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
        </select>
        <button onClick={load} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Refresh</button>
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{['Order', 'RMA', 'Reason', 'Amount', 'Status', 'Actions'].map(h => <th key={h} className="text-left p-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {refunds.map(r => (
              <tr key={r.id} className="border-t">
                <td className="p-2 font-mono text-xs">{r.order_number}</td>
                <td className="p-2 text-xs">{r.rma_number}</td>
                <td className="p-2 max-w-[200px] truncate text-muted-foreground">{r.reason}</td>
                <td className="p-2">${r.refund_amount.toFixed(2)}</td>
                <td className="p-2"><StatusBadge status={r.status} /></td>
                <td className="p-2">
                  {r.status === 'requested' && (
                    <div className="flex gap-1">
                      <button onClick={() => approve(r.id)} className="px-2 py-1 bg-green-600 text-white rounded text-xs">Approve</button>
                      <button onClick={() => reject(r.id)} className="px-2 py-1 bg-red-600 text-white rounded text-xs">Reject</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ───────── Knowledge Base Tab ───────── */
function KnowledgeTab() {
  const [files, setFiles] = useState<KBFile[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const load = useCallback(() => { adminApi.listKnowledgeBase().then(r => setFiles(r.files)) }, [])
  useEffect(() => { load() }, [load])

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setMessage('')
    try {
      const result = await adminApi.uploadKnowledgeBase(file)
      setMessage(`Uploaded: ${result.chunks_ingested} chunks ingested`)
      load()
    } catch (err: any) {
      setMessage(`Error: ${err?.response?.data?.detail || err.message}`)
    }
    setLoading(false)
  }

  const deleteFile = async (name: string) => {
    if (!confirm(`Delete ${name}? This will rebuild the vector store.`)) return
    setLoading(true)
    try {
      await adminApi.deleteKnowledgeBaseFile(name)
      setMessage(`Deleted ${name} and rebuilt vector store`)
      load()
    } catch (err: any) {
      setMessage(`Error: ${err?.response?.data?.detail || err.message}`)
    }
    setLoading(false)
  }

  const rebuild = async () => {
    if (!confirm('Rebuild vector store from all files?')) return
    setLoading(true)
    setMessage('')
    try {
      const result = await adminApi.rebuildKnowledgeBase()
      setMessage(`Rebuilt: ${result.total_chunks || 0} chunks from ${result.files_processed || 0} files`)
      load()
    } catch (err: any) {
      setMessage(`Error: ${err?.response?.data?.detail || err.message}`)
    }
    setLoading(false)
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold flex-1">Knowledge Base</h2>
        <label className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm cursor-pointer">
          {loading ? 'Uploading...' : 'Upload File'}
          <input type="file" className="hidden" accept=".md,.txt,.pdf,.html" onChange={upload} disabled={loading} />
        </label>
        <button onClick={rebuild} disabled={loading} className="px-3 py-1.5 bg-yellow-600 text-white rounded text-sm">Rebuild</button>
      </div>
      {message && <div className="mb-3 p-2 bg-muted rounded text-sm">{message}</div>}
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{['Filename', 'Size', 'Last Modified', ''].map(h => <th key={h} className="text-left p-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {files.map(f => (
              <tr key={f.name} className="border-t">
                <td className="p-2">{f.name}</td>
                <td className="p-2 text-muted-foreground">{(f.size_bytes / 1024).toFixed(1)} KB</td>
                <td className="p-2 text-muted-foreground">{new Date(f.last_modified).toLocaleString()}</td>
                <td className="p-2">
                  <button onClick={() => deleteFile(f.name)} className="text-red-500 hover:text-red-700 text-xs">Delete</button>
                </td>
              </tr>
            ))}
            {files.length === 0 && <tr><td colSpan={4} className="p-4 text-center text-muted-foreground">No documents uploaded</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ───────── Analytics Tab ───────── */
function AnalyticsTab() {
  const [data, setData] = useState<any>(null)
  useEffect(() => { adminApi.getAnalyticsOverview().then(setData) }, [])
  if (!data) return <div className="flex justify-center py-20"><Spinner /></div>
  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Analytics</h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: 'Total Orders', value: data.total_orders },
          { label: 'Total Tickets', value: data.total_tickets },
          { label: 'Resolved', value: data.resolved_tickets },
          { label: 'Resolution Rate', value: `${data.resolution_rate}%` },
          { label: 'Active Sessions', value: data.active_sessions },
        ].map(c => (
          <div key={c.label} className="border rounded-lg p-4 bg-card">
            <div className="text-2xl font-bold">{c.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ───────── Conversations Tab ───────── */
function ConversationsTab() {
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [messages, setMessages] = useState<any[]>([])
  const [summary, setSummary] = useState('')
  const [selectedId, setSelectedId] = useState('')

  useEffect(() => { adminApi.listSessions(0, 100).then(r => setSessions(r.sessions)) }, [])

  const openSession = async (id: string) => {
    setSelectedId(id)
    const d = await adminApi.getSessionMessages(id)
    setMessages(d.messages)
    setSummary(d.summary)
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-12rem)]">
      <div className="w-72 shrink-0 border rounded-lg overflow-y-auto">
        <h3 className="font-semibold p-3 border-b sticky top-0 bg-background">Sessions</h3>
        {sessions.map(s => (
          <div key={s.session_id} className={`p-3 border-b text-sm cursor-pointer hover:bg-muted/30 ${selectedId === s.session_id ? 'bg-muted/50' : ''}`}
            onClick={() => openSession(s.session_id)}>
            <div className="font-mono text-xs truncate">{s.session_id}</div>
            <div className="text-xs text-muted-foreground">{s.message_count} messages</div>
          </div>
        ))}
      </div>
      <div className="flex-1 border rounded-lg overflow-y-auto p-4">
        {summary && <div className="text-sm p-2 bg-muted rounded mb-4"><span className="font-medium">Summary:</span> {summary}</div>}
        {messages.length === 0 && <div className="text-center text-muted-foreground py-10">Select a session to view messages</div>}
        {messages.map((m, i) => (
          <div key={i} className={`mb-3 text-sm ${m.role === 'user' ? 'text-left' : 'text-left bg-muted/30 p-3 rounded'}`}>
            <span className="font-medium text-xs text-muted-foreground">{m.role === 'user' ? 'Customer' : 'Assistant'}</span>
            <div className="mt-1 whitespace-pre-wrap">{m.content}</div>
            {m.timestamp && <div className="text-[10px] text-muted-foreground mt-1">{new Date(m.timestamp).toLocaleString()}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ───────── Users Tab ───────── */
function UsersTab() {
  const [users, setUsers] = useState<UserItem[]>([])
  const [search, setSearch] = useState('')

  const load = useCallback(() => { adminApi.listUsers(0, 100, search || undefined).then(r => setUsers(r.users)) }, [search])
  useEffect(() => { load() }, [load])

  const changeRole = async (id: string, role: string) => {
    await adminApi.updateUserRole(id, role)
    load()
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold flex-1">Users</h2>
        <input className="border rounded px-3 py-1.5 text-sm bg-background w-64" placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)} />
        <button onClick={load} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Refresh</button>
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{['Username', 'Email', 'Name', 'Role', 'Active', 'Verified', ''].map(h => <th key={h} className="text-left p-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-t">
                <td className="p-2">{u.username}</td>
                <td className="p-2 text-muted-foreground">{u.email}</td>
                <td className="p-2">{u.display_name || '-'}</td>
                <td className="p-2">
                  <select className="border rounded px-1 py-0.5 text-xs bg-background" value={u.role} onChange={e => changeRole(u.id, e.target.value)}>
                    {['user', 'admin', 'premium', 'support'].map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="p-2">{u.is_active ? 'Yes' : 'No'}</td>
                <td className="p-2">{u.is_verified ? 'Yes' : 'No'}</td>
                <td className="p-2 text-xs text-muted-foreground">{u.created_at ? new Date(u.created_at).toLocaleDateString() : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ───────── Health Tab ───────── */
function HealthTab() {
  const [health, setHealth] = useState<HealthCheck | null>(null)

  const load = useCallback(() => { adminApi.getHealth().then(setHealth) }, [])
  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold flex-1">System Health</h2>
        <button onClick={load} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Refresh</button>
      </div>
      {health && (
        <div>
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium mb-4 ${health.overall === 'healthy' ? 'bg-green-500/20 text-green-600' : 'bg-yellow-500/20 text-yellow-600'}`}>
            <div className={`w-2 h-2 rounded-full ${health.overall === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'}`} />
            {health.overall === 'healthy' ? 'All Systems Healthy' : 'Degraded'}
          </div>
          <div className="grid gap-3">
            {Object.entries(health.checks).map(([name, check]) => (
              <div key={name} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-semibold capitalize">{name.replace(/_/g, ' ')}</h3>
                  <StatusBadge status={check.status} />
                </div>
                <p className="text-sm text-muted-foreground">{check.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ───────── Main Admin Page ───────── */
export default function AdminPage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')

  if (!user || (user.role !== 'admin' && user.role !== 'support')) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-muted-foreground">You need admin privileges to access this page.</p>
          <a href="/" className="text-primary hover:underline mt-4 inline-block">Back to Chat</a>
        </div>
      </div>
    )
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'dashboard': return <DashboardTab />
      case 'customers': return <CustomersTab />
      case 'orders': return <OrdersTab />
      case 'shipments': return <ShipmentsTab />
      case 'tickets': return <TicketsTab />
      case 'refunds': return <RefundsTab />
      case 'knowledge': return <KnowledgeTab />
      case 'analytics': return <AnalyticsTab />
      case 'conversations': return <ConversationsTab />
      case 'users': return <UsersTab />
      case 'health': return <HealthTab />
    }
  }

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      <nav className="w-56 shrink-0 border-r bg-card overflow-y-auto">
        <div className="p-3 border-b">
          <h1 className="font-bold text-sm">Admin Dashboard</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{user.display_name || user.email}</p>
        </div>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${activeTab === t.id ? 'bg-primary/10 text-primary font-medium border-r-2 border-primary' : 'hover:bg-muted/50 text-muted-foreground'}`}>
            {t.label}
          </button>
        ))}
        <div className="p-3 border-t mt-4">
          <a href="/" className="text-xs text-muted-foreground hover:text-foreground">← Back to Chat</a>
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto p-6">
        {renderTab()}
      </main>
    </div>
  )
}
