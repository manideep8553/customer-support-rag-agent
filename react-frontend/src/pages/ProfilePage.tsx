import { useState, type FormEvent } from 'react'
import { useAuth } from '@/context/AuthContext'
import { updateProfile, changePassword } from '@/api/client'
import { Save, Lock, AlertCircle, Check, ArrowLeft } from 'lucide-react'

export function ProfilePage() {
  const { user, refreshUser, logout } = useAuth()
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [company, setCompany] = useState(user?.company || '')
  const [phone, setPhone] = useState(user?.phone || '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [profileMsg, setProfileMsg] = useState('')
  const [profileErr, setProfileErr] = useState('')
  const [passwordMsg, setPasswordMsg] = useState('')
  const [passwordErr, setPasswordErr] = useState('')
  const [saving, setSaving] = useState(false)

  const handleProfile = async (e: FormEvent) => {
    e.preventDefault()
    setProfileMsg('')
    setProfileErr('')
    setSaving(true)
    try {
      await updateProfile({ display_name: displayName, company, phone })
      await refreshUser()
      setProfileMsg('Profile updated')
    } catch (err: any) {
      setProfileErr(err?.response?.data?.detail || err?.message || 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  const handlePassword = async (e: FormEvent) => {
    e.preventDefault()
    setPasswordMsg('')
    setPasswordErr('')
    if (newPassword.length < 8) {
      setPasswordErr('Password must be at least 8 characters')
      return
    }
    setSaving(true)
    try {
      await changePassword(currentPassword, newPassword)
      setPasswordMsg('Password changed. Other sessions logged out.')
      setCurrentPassword('')
      setNewPassword('')
    } catch (err: any) {
      setPasswordErr(err?.response?.data?.detail || err?.message || 'Password change failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-8">
          <a href="/" className="p-2 rounded-lg hover:bg-secondary text-muted-foreground transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </a>
          <div>
            <h1 className="text-xl font-semibold text-foreground/90">Profile</h1>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Profile Form */}
          <form onSubmit={handleProfile} className="bg-card border border-border rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-foreground/80">Account Details</h2>

            {profileMsg && (
              <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20">
                <Check className="h-4 w-4" />
                <span>{profileMsg}</span>
              </div>
            )}
            {profileErr && (
              <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
                <AlertCircle className="h-4 w-4" />
                <span>{profileErr}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Email</label>
                <input disabled value={user?.email || ''} className="w-full h-9 px-3 rounded-lg border border-border bg-muted text-sm text-foreground/60" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Username</label>
                <input disabled value={user?.username || ''} className="w-full h-9 px-3 rounded-lg border border-border bg-muted text-sm text-foreground/60" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Display Name</label>
                <input value={displayName} onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Company</label>
                <input value={company} onChange={(e) => setCompany(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Phone</label>
                <input value={phone} onChange={(e) => setPhone(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Role</label>
                <input disabled value={user?.role || 'user'} className="w-full h-9 px-3 rounded-lg border border-border bg-muted text-sm text-foreground/60 capitalize" />
              </div>
            </div>
            <button type="submit" disabled={saving}
              className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-all flex items-center gap-2">
              <Save className="h-4 w-4" /> Save Changes
            </button>
          </form>

          {/* Password Form */}
          <form onSubmit={handlePassword} className="bg-card border border-border rounded-xl p-5 space-y-4">
            <h2 className="text-sm font-semibold text-foreground/80">Change Password</h2>

            {passwordMsg && (
              <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20">
                <Check className="h-4 w-4" />
                <span>{passwordMsg}</span>
              </div>
            )}
            {passwordErr && (
              <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
                <AlertCircle className="h-4 w-4" />
                <span>{passwordErr}</span>
              </div>
            )}

            <div className="space-y-3">
              <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Current password" required
                className="w-full h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20" />
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                placeholder="New password" required
                className="w-full h-9 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20" />
            </div>
            <button type="submit" disabled={saving || !currentPassword || !newPassword}
              className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-all flex items-center gap-2">
              <Lock className="h-4 w-4" /> Update Password
            </button>
          </form>

          {/* Sign Out */}
          <div className="text-center">
            <button onClick={logout}
              className="text-sm text-muted-foreground hover:text-destructive transition-colors">
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
