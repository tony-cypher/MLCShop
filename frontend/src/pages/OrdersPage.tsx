import { PackageCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { money, shortDate } from '../lib/format';
import type { Order } from '../types';

export default function OrdersPage() {
  const { user, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    let cancelled = false;

    api<{ data: Order[] }>('/orders')
      .then((response) => {
        if (!cancelled) setOrders(response.data);
      })
      .catch(() => {
        // stay empty
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user, authLoading]);

  if (authLoading || loading) {
    return <div className="empty-state"><span className="empty-state__emoji">⏳</span><h3>Loading orders…</h3></div>;
  }

  if (!user) {
    return (
      <div className="empty-state">
        <span className="empty-state__emoji">🔐</span>
        <h3>Sign in to see your orders</h3>
        <p>Your order history lives with your account.</p>
        <Link to="/login" className="btn btn--primary">
          Sign in
        </Link>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state__emoji">📦</span>
        <h3>No orders yet</h3>
        <p>When you place a test order it will show up here.</p>
        <Link to="/" className="btn btn--primary">
          Start shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="orders-page">
      <div className="page-head">
        <h1>Your Orders</h1>
        <span className="muted">{orders.length} total</span>
      </div>

      <ul className="order-list">
        {orders.map((order) => (
          <li key={order.id} className="order-card">
            <header className="order-card__head">
              <span className="order-card__ref">
                <PackageCheck size={15} /> {order.reference}
              </span>
              <span className={`status-chip status-chip--${order.status}`}>{order.status}</span>
              <time>{shortDate(order.placed_at)}</time>
            </header>

            <ul className="order-card__items">
              {order.items.map((item) => (
                <li key={item.id}>
                  <span className="order-item-line">
                    {item.image_url ? (
                      <img src={item.image_url} alt="" loading="lazy" width={28} height={28} />
                    ) : null}
                    {item.name} × {item.quantity}
                  </span>
                  <span>{money(Number(item.price) * item.quantity)}</span>
                </li>
              ))}
            </ul>

            <footer className="order-card__foot">
              <span>
                {order.delivery_method === 'pickup' ? (
                  <>🏬 Pick up{order.address ? ` · ${Object.values(order.address).join(', ')}` : ''}</>
                ) : (
                  <>🚚 Standard{order.address ? ` · ${order.address.line1}, ${order.address.city}` : ''}</>
                )}
              </span>
              <span>
                Test card •••• {order.card_last4} · <strong>{money(order.total)}</strong>
              </span>
            </footer>
          </li>
        ))}
      </ul>
    </div>
  );
}
