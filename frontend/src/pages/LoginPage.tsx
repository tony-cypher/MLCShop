import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import GoogleButton from '../components/GoogleButton';
import PasswordInput from '../components/PasswordInput';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { ApiError } from '../lib/api';

const OAUTH_ERRORS: Record<string, string> = {
  google: 'Google sign-in was cancelled or failed. Please try again.',
  google_email: 'Your Google account didn’t share an email address with us.',
};

export default function LoginPage() {
  const { login } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const oauthError = searchParams.get('error');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(oauthError ? OAUTH_ERRORS[oauthError] ?? 'Sign in failed.' : null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await login(email.trim(), password);
      push(`Welcome back, ${user.name.split(' ')[0]}!`, 'success');
      navigate('/', { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Sign in failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <h1>Welcome back</h1>
        <p className="muted">Sign in to see your orders and sync favourites.</p>

        {error && <div className="form-alert form-alert--error">{error}</div>}

        <label className="field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
            placeholder="you@example.com"
          />
        </label>

        <PasswordInput
          label="Password"
          value={password}
          onChange={setPassword}
          placeholder="••••••••"
          autoComplete="current-password"
          required
        />

        <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>

        <div className="auth-divider" role="separator">
          <span>or continue with</span>
        </div>

        <GoogleButton />

        <div className="auth-card__foot">
          New here? <Link to="/register">Create an account</Link>
        </div>

        <div className="demo-hint">
          <strong>Demo account</strong>
          <code>demo@mlc.test</code> · <code>password123</code>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              setEmail('demo@mlc.test');
              setPassword('password123');
            }}
          >
            Fill
          </button>
        </div>
      </form>
    </div>
  );
}
