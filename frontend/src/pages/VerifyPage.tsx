import { CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

type Status = 'working' | 'done' | 'failed';

export default function VerifyPage() {
  const [params] = useSearchParams();
  const { verifyEmail } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();

  const [status, setStatus] = useState<Status>('working');
  const [message, setMessage] = useState('');
  const ranRef = useRef(false);

  const token = params.get('token');

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;

    if (!token) {
      setStatus('failed');
      setMessage('This link is missing its confirmation token.');
      return;
    }

    verifyEmail(token)
      .then((user) => {
        setStatus('done');
        setMessage(`You're verified, ${user.name.split(' ')[0]}! Taking you back to the shop…`);
        push('Email confirmed — welcome aboard!', 'success');
        window.setTimeout(() => navigate('/', { replace: true }), 2200);
      })
      .catch((caught: unknown) => {
        setStatus('failed');
        setMessage(caught instanceof Error ? caught.message : 'This link is invalid or expired.');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--center">
        {status === 'working' && (
          <>
            <Loader2 size={40} className="spin" />
            <h1>Confirming your email…</h1>
          </>
        )}

        {status === 'done' && (
          <>
            <span className="verify-icon verify-icon--ok">
              <CheckCircle2 size={44} />
            </span>
            <h1>Email confirmed</h1>
            <p className="muted">{message}</p>
            <Link to="/" className="btn btn--primary btn--block">
              Back to the shop
            </Link>
          </>
        )}

        {status === 'failed' && (
          <>
            <span className="verify-icon verify-icon--bad">
              <XCircle size={44} />
            </span>
            <h1>Confirmation failed</h1>
            <p className="muted">{message}</p>
            <Link to="/login" className="btn btn--primary btn--block">
              Sign in and resend the link
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
