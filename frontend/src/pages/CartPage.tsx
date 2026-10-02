import { Minus, Plus, ShoppingBag, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { money } from '../lib/format';

const FREE_SHIPPING_OVER = 100;
const SHIPPING_FLAT = 9.99;

export default function CartPage() {
  const { items, subtotal, setQuantity, removeItem, clear } = useCart();

  const shipping = subtotal >= FREE_SHIPPING_OVER || subtotal === 0 ? 0 : SHIPPING_FLAT;
  const total = subtotal + shipping;

  if (items.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state__emoji">🛒</span>
        <h3>Your cart is empty</h3>
        <p>Browse the shop and add something you love.</p>
        <Link to="/" className="btn btn--primary">
          Start shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="cart-page">
      <div className="page-head">
        <h1>Your Cart</h1>
        <button type="button" className="link-button" onClick={clear}>
          Clear cart
        </button>
      </div>

      <div className="cart-layout">
        <ul className="cart-list">
          {items.map((item) => (
            <li key={`${item.id}-${item.size ?? ''}-${item.color ?? ''}`} className="cart-row">
              <Link to={`/product/${item.slug}`} className="cart-row__tile">
                {item.image_url ? (
                  <img src={item.image_url} alt="" loading="lazy" width={72} height={72} />
                ) : (
                  item.emoji
                )}
              </Link>

              <div className="cart-row__info">
                <Link to={`/product/${item.slug}`} className="cart-row__name">
                  {item.name}
                </Link>
                {(item.size || item.color) && (
                  <small className="cart-row__variant">
                    {[item.size, item.color].filter(Boolean).join(' · ')}
                  </small>
                )}
                <small className="cart-row__unit">{money(item.price)} each</small>
              </div>

              <div className="qty-stepper qty-stepper--sm">
                <button
                  type="button"
                  onClick={() => setQuantity(item.id, item.quantity - 1, item.size, item.color)}
                  aria-label="Decrease quantity"
                >
                  <Minus size={13} />
                </button>
                <span>{item.quantity}</span>
                <button
                  type="button"
                  onClick={() => setQuantity(item.id, item.quantity + 1, item.size, item.color)}
                  aria-label="Increase quantity"
                >
                  <Plus size={13} />
                </button>
              </div>

              <strong className="cart-row__total">{money(item.price * item.quantity)}</strong>

              <button
                type="button"
                className="icon-button icon-button--danger"
                onClick={() => removeItem(item.id, item.size, item.color)}
                aria-label={`Remove ${item.name}`}
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>

        <aside className="summary-card">
          <h2>Order Summary</h2>

          <dl>
            <div>
              <dt>Subtotal</dt>
              <dd>{money(subtotal)}</dd>
            </div>
            <div>
              <dt>Shipping</dt>
              <dd>{shipping === 0 ? 'Free' : money(shipping)}</dd>
            </div>
            <div className="summary-card__total">
              <dt>Total</dt>
              <dd>{money(total)}</dd>
            </div>
          </dl>

          {shipping > 0 && (
            <p className="summary-card__hint">
              Add {money(FREE_SHIPPING_OVER - subtotal)} more for free standard shipping.
            </p>
          )}

          <Link to="/checkout" className="btn btn--primary btn--block">
            Proceed to checkout
          </Link>

          <p className="summary-card__note">
            <ShoppingBag size={13} /> Test checkout only — no real payment is processed.
          </p>
        </aside>
      </div>
    </div>
  );
}
