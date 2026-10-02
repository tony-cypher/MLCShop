import { MailWarning } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export default function AuthBanner() {
  const { user, resendVerification } = useAuth();
  const { push } = useToast();
  const [sending, setSending] = useState(false);
  const [hidden, setHidden] = useState(false);

  if (!user || user.email_verified_at || hidden) return null;

  return (
    <div className="auth-banner">
      <span className="auth-banner__icon">
        <MailWarning size={16} />
      </span>
      <span>
        Confirm <strong>{user.email}</strong> to secure your account — we sent you a link.
      </span>
      <button
        type="button"
        className="auth-banner__action"
        disabled={sending}
        onClick={async () => {
          setSending(true);
          try {
            const message = await resendVerification();
            push(message, 'success');
          } catch (error) {
            push(error instanceof Error ? error.message : 'Could not send the email', 'error');
          } finally {
            setSending(false);
          }
        }}
      >
        {sending ? 'Sending…' : 'Resend email'}
      </button>
      <button
        type="button"
        className="auth-banner__dismiss"
        onClick={() => setHidden(true)}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
