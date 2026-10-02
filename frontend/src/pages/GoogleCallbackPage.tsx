import { Loader2, XCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { setToken } from '../lib/api';

/**
 * The API's Google callback redirects here with the bearer token in the
 * URL fragment: /auth/google/callback#token=…
 */
export default function GoogleCallbackPage() {
  const [token] = useState(() =>
    new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token'),
  );
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const ran = useRef(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    if (!token) {
      setFailed(true);
      return;
    }

    setToken(token);
    refresh()
      .then(() => navigate('/', { replace: true }))
      .catch(() => {
        setToken(null);
        setFailed(true);
      });
  }, [token, refresh, navigate]);

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--center">
        {failed ? (
          <>
            <span className="verify-icon verify-icon--bad">
              <XCircle size={44} />
            </span>
            <h1>Google sign-in failed</h1>
            <p className="muted">We couldn’t complete the Google sign-in. Please try again.</p>
            <Link to="/login" className="btn btn--primary btn--block">
              Back to sign in
            </Link>
          </>
        ) : (
          <>
            <Loader2 size={40} className="spin" />
            <h1>Signing you in with Google…</h1>
          </>
        )}
      </div>
    </div>
  );
}
