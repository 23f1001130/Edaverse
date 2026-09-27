import React from 'react'
import { useSignIn, useSignUp } from '@clerk/clerk-react'
import './AuthPage.css'

const APP_URL = import.meta.env.VITE_APP_URL || window.location.origin

// Only list providers actually enabled in the Clerk dashboard (User & Authentication →
// Social Connections) — an unlisted strategy fails at authenticateWithRedirect().
const SOCIAL_PROVIDERS = [
  {
    strategy: 'oauth_google',
    label: 'Google',
    icon: (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor">
        <path d="M23.5 12.27c0-.79-.07-1.54-.2-2.27H12v4.51h6.47a5.54 5.54 0 0 1-2.4 3.64v3h3.86c2.26-2.09 3.57-5.17 3.57-8.88z" opacity=".6"/>
        <path d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.07.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09A12 12 0 0 0 12 24z" opacity=".8"/>
        <path d="M5.27 14.28A7.2 7.2 0 0 1 4.89 12c0-.79.14-1.56.38-2.28V6.63H1.29A12 12 0 0 0 0 12c0 1.94.46 3.77 1.29 5.37z" opacity=".4"/>
        <path d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.94 1.19 15.24 0 12 0A12 12 0 0 0 1.29 6.63l3.98 3.09C6.22 6.87 8.87 4.75 12 4.75z"/>
      </svg>
    ),
  },
  // To add GitHub (or any other provider): enable it in the Clerk dashboard under
  // Social Connections first, then uncomment/add its entry here with a matching icon.
]

function EyeIcon({ open }) {
  return open ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-6.5 0-10-7-10-7a18.7 18.7 0 0 1 4.22-5.17M9.9 4.24A10.94 10.94 0 0 1 12 4c6.5 0 10 7 10 7a18.7 18.7 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
      <line x1="2" y1="2" x2="22" y2="22"/>
    </svg>
  )
}

function clerkErrorMessage(err, fallback) {
  return err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || fallback
}

export default function AuthPage({ onSuccess, onBack }) {
  const { isLoaded: signInLoaded, signIn, setActive: setActiveSignIn } = useSignIn()
  const { isLoaded: signUpLoaded, signUp, setActive: setActiveSignUp } = useSignUp()

  const [mode, setMode] = React.useState('signup') // signup | signin
  const [step, setStep] = React.useState('form') // form | verify-email | forgot-email | forgot-code | forgot-password
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [newPassword, setNewPassword] = React.useState('')
  const [code, setCode] = React.useState('')
  const [showPassword, setShowPassword] = React.useState(false)
  const [loading, setLoading] = React.useState(false)
  const [socialLoading, setSocialLoading] = React.useState(null)
  const [error, setError] = React.useState('')
  const [resendCooldown, setResendCooldown] = React.useState(0)

  React.useEffect(() => {
    if (resendCooldown <= 0) return
    const t = setTimeout(() => setResendCooldown((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [resendCooldown])

  function switchMode(next) {
    setMode(next)
    setStep('form')
    setError('')
    setCode('')
    setPassword('')
    setNewPassword('')
  }

  async function handleSocial(strategy) {
    setError('')
    setSocialLoading(strategy)
    try {
      const client = mode === 'signup' ? signUp : signIn
      await client.authenticateWithRedirect({
        strategy,
        redirectUrl: `${APP_URL}/sso-callback`,
        redirectUrlComplete: APP_URL,
      })
    } catch (err) {
      setError(clerkErrorMessage(err, 'Could not start social sign-in.'))
      setSocialLoading(null)
    }
  }

  async function handleSignUp(e) {
    e.preventDefault()
    if (!signUpLoaded) return
    setError('')
    setLoading(true)
    try {
      await signUp.create({ emailAddress: email, password })
      await signUp.prepareEmailAddressVerification({ strategy: 'email_code' })
      setStep('verify-email')
      setResendCooldown(30)
    } catch (err) {
      setError(clerkErrorMessage(err, 'Could not create your account.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifyEmail(e) {
    e.preventDefault()
    if (!signUpLoaded) return
    setError('')
    setLoading(true)
    try {
      const result = await signUp.attemptEmailAddressVerification({ code })
      if (result.status === 'complete') {
        await setActiveSignUp({ session: result.createdSessionId })
        onSuccess?.()
      } else {
        setError('Verification incomplete. Please try again.')
      }
    } catch (err) {
      setError(clerkErrorMessage(err, 'Invalid or expired code.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleResendCode() {
    if (resendCooldown > 0 || !signUpLoaded) return
    setError('')
    try {
      await signUp.prepareEmailAddressVerification({ strategy: 'email_code' })
      setResendCooldown(30)
    } catch (err) {
      setError(clerkErrorMessage(err, 'Could not resend the code.'))
    }
  }

  async function handleSignIn(e) {
    e.preventDefault()
    if (!signInLoaded) return
    setError('')
    setLoading(true)
    try {
      const result = await signIn.create({ identifier: email, password })
      if (result.status === 'complete') {
        await setActiveSignIn({ session: result.createdSessionId })
        onSuccess?.()
      } else {
        setError('Additional verification is required for this account.')
      }
    } catch (err) {
      setError(clerkErrorMessage(err, 'Could not sign you in.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleForgotEmail(e) {
    e.preventDefault()
    if (!signInLoaded) return
    setError('')
    setLoading(true)
    try {
      const attempt = await signIn.create({ identifier: email })
      const factor = attempt.supportedFirstFactors?.find((f) => f.strategy === 'reset_password_email_code')
      if (!factor) throw new Error('Password reset is not available for this account.')
      await signIn.prepareFirstFactor({ strategy: 'reset_password_email_code', emailAddressId: factor.emailAddressId })
      setStep('forgot-code')
      setResendCooldown(30)
    } catch (err) {
      setError(clerkErrorMessage(err, 'Could not find an account with that email.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleForgotCode(e) {
    e.preventDefault()
    if (!signInLoaded) return
    setError('')
    setLoading(true)
    try {
      const result = await signIn.attemptFirstFactor({ strategy: 'reset_password_email_code', code })
      if (result.status === 'needs_new_password') {
        setStep('forgot-password')
      } else {
        setError('Verification incomplete. Please try again.')
      }
    } catch (err) {
      setError(clerkErrorMessage(err, 'Invalid or expired code.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleForgotReset(e) {
    e.preventDefault()
    if (!signInLoaded) return
    setError('')
    setLoading(true)
    try {
      const result = await signIn.resetPassword({ password: newPassword })
      if (result.status === 'complete') {
        await setActiveSignIn({ session: result.createdSessionId })
        onSuccess?.()
      } else {
        setError('Could not reset your password. Please try again.')
      }
    } catch (err) {
      setError(clerkErrorMessage(err, 'Could not reset your password.'))
    } finally {
      setLoading(false)
    }
  }

  const busy = loading || !!socialLoading

  return (
    <div className="auth-page">
      <div className="auth-shell">
        <section className="auth-story" aria-label="Product preview">
          <button className="auth-back" onClick={onBack} type="button">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            Back
          </button>
          <div className="auth-logo">
            <span className="auth-logo-mark">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" rx="1.5"/>
                <rect x="14" y="3" width="7" height="7" rx="1.5"/>
                <rect x="3" y="14" width="7" height="7" rx="1.5"/>
                <rect x="14" y="14" width="7" height="7" rx="1.5"/>
              </svg>
            </span>
            <span className="auth-logo-name">edaverse</span>
          </div>

          <div className="auth-story-copy">
            <span className="auth-kicker">Private data workspace</span>
            <h1>Secure access for serious analysis.</h1>
            <p>Keep uploads, cleaning decisions, AI notes, and export-ready datasets attached to one protected workspace.</p>
          </div>

          <div className="auth-preview">
            <div className="auth-preview-head">
              <div>
                <span>workspace audit</span>
                <strong>customer_churn.csv</strong>
              </div>
              <em>Live</em>
            </div>
            <div className="auth-preview-metrics">
              <div><span>Datasets</span><strong>12</strong></div>
              <div><span>Exports</span><strong>31</strong></div>
              <div><span>Quality</span><strong>94</strong></div>
            </div>
            <div className="auth-preview-body">
              <div className="auth-preview-chart" aria-hidden="true">
                {[72, 46, 88, 62, 54, 79, 41].map((height, index) => (
                  <span key={index} style={{ height: `${height}%` }} />
                ))}
              </div>
              <div className="auth-preview-list">
                <span><i /> Email verified</span>
                <span><i /> Analysis history synced</span>
                <span><i /> Demo access available</span>
              </div>
            </div>
          </div>

          <div className="auth-assurance">
            <span>Verified sign-in</span>
            <span>No raw-data marketing use</span>
            <span>Domain-ready email links</span>
          </div>
        </section>

        <section className="auth-panel" aria-label="Authentication form">
          <div className="auth-panel-head">
            <span className="auth-panel-eyebrow">Account access</span>
            <h2>
              {step === 'verify-email' && 'Check your inbox'}
              {step === 'forgot-email' && 'Reset your password'}
              {step === 'forgot-code' && 'Enter the reset code'}
              {step === 'forgot-password' && 'Choose a new password'}
              {step === 'form' && (mode === 'signup' ? 'Create your workspace' : 'Sign in to continue')}
            </h2>
            <p>
              {step === 'verify-email' && `We sent a 6-digit code to ${email}.`}
              {step === 'forgot-email' && 'Enter your email and we’ll send you a reset code.'}
              {step === 'forgot-code' && `Enter the code we sent to ${email}.`}
              {step === 'forgot-password' && 'Set a new password for your account.'}
              {step === 'form' && (mode === 'signup' ? 'Start with secure access and saved analysis history.' : 'Open your saved datasets and continue your analysis.')}
            </p>
          </div>

          {step === 'form' && (
            <div className="auth-switch" role="tablist" aria-label="Authentication mode">
              <button
                className={mode === 'signup' ? 'active' : ''}
                onClick={() => switchMode('signup')}
                type="button"
                role="tab"
                aria-selected={mode === 'signup'}
              >
                Create account
              </button>
              <button
                className={mode === 'signin' ? 'active' : ''}
                onClick={() => switchMode('signin')}
                type="button"
                role="tab"
                aria-selected={mode === 'signin'}
              >
                Sign in
              </button>
            </div>
          )}

          <div className="auth-card">
            {error && <div className="auth-error" role="alert">{error}</div>}

            {step === 'form' && (
              <>
                <div className="auth-social">
                  {SOCIAL_PROVIDERS.map((p) => (
                    <button
                      key={p.strategy}
                      type="button"
                      className="auth-social-btn"
                      disabled={busy}
                      onClick={() => handleSocial(p.strategy)}
                    >
                      {socialLoading === p.strategy ? <span className="auth-spinner" /> : p.icon}
                      Continue with {p.label}
                    </button>
                  ))}
                </div>

                <div className="auth-divider"><span>or</span></div>

                <form className="auth-form" onSubmit={mode === 'signup' ? handleSignUp : handleSignIn}>
                  <label className="auth-field">
                    <span>Email address</span>
                    <input
                      type="email"
                      required
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                    />
                  </label>

                  <label className="auth-field">
                    <span>Password</span>
                    <div className="auth-input-wrap">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        minLength={8}
                        autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="At least 8 characters"
                      />
                      <button
                        type="button"
                        className="auth-input-icon-btn"
                        onClick={() => setShowPassword((s) => !s)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        <EyeIcon open={showPassword} />
                      </button>
                    </div>
                  </label>

                  {mode === 'signup' && <div id="clerk-captcha" />}

                  {mode === 'signin' && (
                    <button
                      type="button"
                      className="auth-link-btn"
                      onClick={() => { setError(''); setStep('forgot-email') }}
                    >
                      Forgot password?
                    </button>
                  )}

                  <button type="submit" className="auth-submit" disabled={busy}>
                    {loading ? <span className="auth-spinner" /> : (mode === 'signup' ? 'Create account' : 'Sign in')}
                  </button>
                </form>
              </>
            )}

            {step === 'verify-email' && (
              <form className="auth-form" onSubmit={handleVerifyEmail}>
                <label className="auth-field">
                  <span>Verification code</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    required
                    className="auth-otp-input"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="000000"
                  />
                </label>
                <button type="submit" className="auth-submit" disabled={busy || code.length < 6}>
                  {loading ? <span className="auth-spinner" /> : 'Verify email'}
                </button>
                <button
                  type="button"
                  className="auth-link-btn auth-link-btn-center"
                  disabled={resendCooldown > 0}
                  onClick={handleResendCode}
                >
                  {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend code'}
                </button>
              </form>
            )}

            {step === 'forgot-email' && (
              <form className="auth-form" onSubmit={handleForgotEmail}>
                <label className="auth-field">
                  <span>Email address</span>
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                  />
                </label>
                <button type="submit" className="auth-submit" disabled={busy}>
                  {loading ? <span className="auth-spinner" /> : 'Send reset code'}
                </button>
                <button type="button" className="auth-link-btn auth-link-btn-center" onClick={() => switchMode('signin')}>
                  Back to sign in
                </button>
              </form>
            )}

            {step === 'forgot-code' && (
              <form className="auth-form" onSubmit={handleForgotCode}>
                <label className="auth-field">
                  <span>Reset code</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    required
                    className="auth-otp-input"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="000000"
                  />
                </label>
                <button type="submit" className="auth-submit" disabled={busy || code.length < 6}>
                  {loading ? <span className="auth-spinner" /> : 'Continue'}
                </button>
                <button
                  type="button"
                  className="auth-link-btn auth-link-btn-center"
                  disabled={resendCooldown > 0}
                  onClick={handleForgotEmail}
                >
                  {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend code'}
                </button>
              </form>
            )}

            {step === 'forgot-password' && (
              <form className="auth-form" onSubmit={handleForgotReset}>
                <label className="auth-field">
                  <span>New password</span>
                  <div className="auth-input-wrap">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 8 characters"
                    />
                    <button
                      type="button"
                      className="auth-input-icon-btn"
                      onClick={() => setShowPassword((s) => !s)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      <EyeIcon open={showPassword} />
                    </button>
                  </div>
                </label>
                <button type="submit" className="auth-submit" disabled={busy}>
                  {loading ? <span className="auth-spinner" /> : 'Reset password'}
                </button>
              </form>
            )}
          </div>

          <div className="auth-footnotes" aria-label="Security details">
            <span>Session protected</span>
            <span>Private uploads</span>
            <span>Domain-ready emails</span>
          </div>
        </section>
      </div>
    </div>
  )
}
