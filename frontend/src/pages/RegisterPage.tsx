import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import GoogleButton from '../components/GoogleButton';
import PasswordInput from '../components/PasswordInput';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { ApiError } from '../lib/api';

export default function RegisterPage() {
  const { register } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirmation, setPasswordConfirmation] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== passwordConfirmation) {
      setError('The two passwords don’t match.');
      return;
    }

    setSubmitting(true);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        passwordConfirmation,
      });
      push('Account created — check your inbox for the confirmation link.', 'success');
      navigate('/', { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError) {
        const first = Object.values(caught.errors)[0]?.[0];
        setError(first ?? caught.message);
      } else {
        setError('Could not create the account. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <h1>Create your account</h1>
        <p className="muted">Join MLC to track orders and sync favourites.</p>

        {error && <div className="form-alert form-alert--error">{error}</div>}

        <label className="field">
          <span>Name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            autoComplete="name"
            placeholder="Ada Lovelace"
          />
        </label>

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
          placeholder="At least 8 characters"
          autoComplete="new-password"
          required
          minLength={8}
        />

        <PasswordInput
          label="Confirm password"
          value={passwordConfirmation}
          onChange={setPasswordConfirmation}
          placeholder="Repeat your password"
          autoComplete="new-password"
          required
        />

        <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>

        <div className="auth-divider" role="separator">
          <span>or sign up with</span>
        </div>

        <GoogleButton label="Sign up with Google" />

        <p className="auth-card__note">
          We’ll email you a confirmation link (via Mailgun once configured).
        </p>

        <div className="auth-card__foot">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </form>
    </div>
  );
}
