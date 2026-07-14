import { useState, type FormEvent } from 'react'
import { useAuth } from '@/context/AuthContext'
import { UserPlus, Mail, Lock, User, Eye, EyeOff, AlertCircle, Check } from 'lucide-react'

export function RegisterPage() {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const passwordChecks = {
    length: password.length >= 8,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    digit: /\d/.test(password),
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!passwordChecks.length || !passwordChecks.upper || !passwordChecks.lower || !passwordChecks.digit) {
      setError('Password does not meet requirements')
      return
    }
    setError('')
    setLoading(true)
    try {
      await register(email, username, password, displayName || undefined)
      window.location.href = '/'
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const CheckItem = ({ ok, label }: { ok: boolean; label: string }) => (
    <div className={`flex items-center gap-1.5 text-xs ${ok ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground/60'}`}>
      <Check className={`h-3 w-3 ${ok ? 'opacity-100' : 'opacity-30'}`} />
      <span>{label}</span>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-4">
            <span className="text-xl font-bold text-primary">G</span>
          </div>
          <h1 className="text-2xl font-semibold text-foreground/90">Create account</h1>
          <p className="text-sm text-muted-foreground mt-1">Join GigaCorp Support</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-foreground/80 mb-1.5">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full h-10 pl-9 pr-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/80 mb-1.5">Username</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value.replace(/[^a-zA-Z0-9_]/g, ''))}
                placeholder="your_username"
                required
                className="w-full h-10 pl-9 pr-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/80 mb-1.5">
              Display name <span className="text-muted-foreground/60">(optional)</span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Jane Doe"
              className="w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/80 mb-1.5">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a strong password"
                required
                className="w-full h-10 pl-9 pr-10 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {password.length > 0 && (
              <div className="mt-2 space-y-1">
                <CheckItem ok={passwordChecks.length} label="At least 8 characters" />
                <CheckItem ok={passwordChecks.upper} label="One uppercase letter" />
                <CheckItem ok={passwordChecks.lower} label="One lowercase letter" />
                <CheckItem ok={passwordChecks.digit} label="One digit" />
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-10 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <UserPlus className="h-4 w-4" />
            )}
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-muted-foreground mt-6">
          Already have an account?{' '}
          <a href="/login" className="text-primary hover:text-primary/80 font-medium transition-colors">
            Sign in
          </a>
        </p>
      </div>
    </div>
  )
}
