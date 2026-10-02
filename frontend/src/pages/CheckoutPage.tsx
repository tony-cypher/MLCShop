import { CheckCircle2, CreditCard, Lock, ShoppingBag, Truck, Store } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useToast } from '../context/ToastContext';
import { ApiError, api } from '../lib/api';
import { money } from '../lib/format';
import type { DeliveryMethod, Order } from '../types';

const FREE_SHIPPING_OVER = 100;
const SHIPPING_FLAT = 9.99;

interface AddressForm {
  line1: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}

export default function CheckoutPage() {
  const { items, subtotal, clear } = useCart();
  const { user } = useAuth();
  const { push } = useToast();

  const [name, setName] = useState(user?.name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [phone, setPhone] = useState('');
  const [delivery, setDelivery] = useState<DeliveryMethod>('standard');
  const [address, setAddress] = useState<AddressForm>({
    line1: '',
    city: '',
    state: '',
    zip: '',
    country: '',
  });

  const [cardholder, setCardholder] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [placedOrder, setPlacedOrder] = useState<Order | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const shipping = useMemo(() => {
    if (delivery === 'pickup') return 0;
    return subtotal >= FREE_SHIPPING_OVER ? 0 : SHIPPING_FLAT;
  }, [delivery, subtotal]);
  const total = subtotal + shipping;

  if (placedOrder) {
    return (
      <div className="checkout-success">
        <span className="checkout-success__icon">
          <CheckCircle2 size={54} />
        </span>
        <h1>Order confirmed!</h1>
        <p className="checkout-success__ref">
          Reference <strong>{placedOrder.reference}</strong>
        </p>
        <p className="muted">
          This was a <strong>test order</strong> — your card was not charged. A confirmation email
          was sent to <strong>{placedOrder.email}</strong>
          {user ? '' : ' (check your inbox — in dev mode it is written to the server log)'}.
        </p>

        <div className="checkout-success__card">
          {placedOrder.items.map((item) => (
            <div key={item.id} className="checkout-success__line">
              <span className="checkout-success__line-item">
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt=""
                    loading="lazy"
                    width={28}
                    height={28}
                  />
                ) : null}
                {item.name} × {item.quantity}
              </span>
              <span>{money(Number(item.price) * item.quantity)}</span>
            </div>
          ))}
          <div className="checkout-success__line checkout-success__line--total">
            <span>Total paid ({placedOrder.delivery_method === 'pickup' ? 'Pick Up' : 'Standard'})</span>
            <strong>{money(placedOrder.total)}</strong>
          </div>
        </div>

        <div className="checkout-success__actions">
          {user ? (
            <Link to="/orders" className="btn btn--primary">
              View my orders
            </Link>
          ) : (
            <Link to="/login" className="btn btn--primary">
              Sign in to track orders
            </Link>
          )}
          <Link to="/" className="btn btn--outline">
            Continue shopping
          </Link>
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return <Navigate to="/cart" replace />;
  }

  async function placeOrder(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    setFieldErrors({});

    try {
      const response = await api<{ data: Order; message: string }>('/checkout', {
        method: 'POST',
        body: {
          items: items.map((item) => ({ product_id: item.id, quantity: item.quantity })),
          customer: {
            name: name.trim(),
            email: email.trim(),
            phone: phone.trim() || undefined,
          },
          delivery_method: delivery,
          address: delivery === 'standard' ? address : undefined,
          payment: {
            cardholder: cardholder.trim(),
            card_number: cardNumber,
            expiry,
            cvc,
          },
        },
      });

      setPlacedOrder(response.data);
      clear();
      push(response.message, 'success');
      window.scrollTo({ top: 0 });
    } catch (caught) {
      if (caught instanceof ApiError) {
        const mapped: Record<string, string> = {};
        Object.entries(caught.errors).forEach(([key, messages]) => {
          mapped[key] = messages[0];
        });
        setFieldErrors(mapped);
        setFormError(caught.message);
        push(caught.message, 'error');
      } else {
        setFormError('Something went wrong. Please try again.');
        push('Something went wrong. Please try again.', 'error');
      }
    } finally {
      setSubmitting(false);
    }
  }

  function formatCardNumber(value: string) {
    const digits = value.replace(/\D/g, '').slice(0, 16);
    return digits.replace(/(.{4})/g, '$1 ').trim();
  }

  return (
    <div className="checkout-page">
      <div className="page-head">
        <h1>Checkout</h1>
        <span className="test-mode-chip">
          <Lock size={13} /> Test mode — no real charge
        </span>
      </div>

      <form className="checkout-layout" onSubmit={placeOrder}>
        <div className="checkout-form">
          {formError && <div className="form-alert form-alert--error">{formError}</div>}

          <section className="form-card">
            <h2>Contact</h2>
            <div className="form-grid form-grid--2">
              <label className="field">
                <span>Full name</span>
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                  autoComplete="name"
                  placeholder="Ada Lovelace"
                />
                {fieldErrors['customer.name'] && (
                  <em className="field__error">{fieldErrors['customer.name']}</em>
                )}
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
                {fieldErrors['customer.email'] && (
                  <em className="field__error">{fieldErrors['customer.email']}</em>
                )}
              </label>
              <label className="field">
                <span>Phone (optional)</span>
                <input
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  autoComplete="tel"
                  placeholder="+1 555 000 1234"
                />
              </label>
            </div>
          </section>

          <section className="form-card">
            <h2>Delivery</h2>
            <div className="delivery-cards">
              <button
                type="button"
                className={`delivery-card ${delivery === 'standard' ? 'is-active' : ''}`}
                onClick={() => setDelivery('standard')}
              >
                <Truck size={18} />
                <span>
                  <strong>Standard</strong>
                  <small>
                    {subtotal >= FREE_SHIPPING_OVER ? 'Free over $100' : `${money(SHIPPING_FLAT)} — free over $100`}
                  </small>
                </span>
              </button>
              <button
                type="button"
                className={`delivery-card ${delivery === 'pickup' ? 'is-active' : ''}`}
                onClick={() => setDelivery('pickup')}
              >
                <Store size={18} />
                <span>
                  <strong>Pick Up</strong>
                  <small>Free — ready in 2 hours</small>
                </span>
              </button>
            </div>

            {delivery === 'standard' && (
              <div className="form-grid">
                <label className="field">
                  <span>Street address</span>
                  <input
                    value={address.line1}
                    onChange={(event) => setAddress({ ...address, line1: event.target.value })}
                    required
                    autoComplete="address-line1"
                    placeholder="12 Purple Avenue"
                  />
                  {fieldErrors['address.line1'] && (
                    <em className="field__error">{fieldErrors['address.line1']}</em>
                  )}
                </label>
                <div className="form-grid form-grid--3">
                  <label className="field">
                    <span>City</span>
                    <input
                      value={address.city}
                      onChange={(event) => setAddress({ ...address, city: event.target.value })}
                      required
                      autoComplete="address-level2"
                      placeholder="Lagos"
                    />
                    {fieldErrors['address.city'] && (
                      <em className="field__error">{fieldErrors['address.city']}</em>
                    )}
                  </label>
                  <label className="field">
                    <span>State</span>
                    <input
                      value={address.state}
                      onChange={(event) => setAddress({ ...address, state: event.target.value })}
                      required
                      autoComplete="address-level1"
                      placeholder="LA"
                    />
                    {fieldErrors['address.state'] && (
                      <em className="field__error">{fieldErrors['address.state']}</em>
                    )}
                  </label>
                  <label className="field">
                    <span>ZIP / Postal</span>
                    <input
                      value={address.zip}
                      onChange={(event) => setAddress({ ...address, zip: event.target.value })}
                      required
                      autoComplete="postal-code"
                      placeholder="100001"
                    />
                    {fieldErrors['address.zip'] && (
                      <em className="field__error">{fieldErrors['address.zip']}</em>
                    )}
                  </label>
                </div>
                <label className="field">
                  <span>Country</span>
                  <input
                    value={address.country}
                    onChange={(event) => setAddress({ ...address, country: event.target.value })}
                    required
                    autoComplete="country-name"
                    placeholder="Nigeria"
                  />
                  {fieldErrors['address.country'] && (
                    <em className="field__error">{fieldErrors['address.country']}</em>
                  )}
                </label>
              </div>
            )}
          </section>

          <section className="form-card">
            <h2>
              <CreditCard size={16} /> Payment <span className="form-card__tag">TEST ONLY</span>
            </h2>
            <div className="form-alert form-alert--info">
              Nothing is charged. Use the test card <strong>4242 4242 4242 4242</strong>, any future
              expiry, any CVC.
            </div>

            <div className="form-grid">
              <label className="field">
                <span>Cardholder name</span>
                <input
                  value={cardholder}
                  onChange={(event) => setCardholder(event.target.value)}
                  required
                  autoComplete="cc-name"
                  placeholder="Ada Lovelace"
                />
                {fieldErrors['payment.cardholder'] && (
                  <em className="field__error">{fieldErrors['payment.cardholder']}</em>
                )}
              </label>
              <label className="field">
                <span>Card number</span>
                <input
                  value={cardNumber}
                  onChange={(event) => setCardNumber(formatCardNumber(event.target.value))}
                  required
                  inputMode="numeric"
                  autoComplete="cc-number"
                  placeholder="4242 4242 4242 4242"
                />
                {fieldErrors['payment.card_number'] && (
                  <em className="field__error">{fieldErrors['payment.card_number']}</em>
                )}
              </label>
              <div className="form-grid form-grid--2">
                <label className="field">
                  <span>Expiry (MM/YY)</span>
                  <input
                    value={expiry}
                    onChange={(event) => setExpiry(event.target.value.replace(/[^0-9/]/g, '').slice(0, 5))}
                    required
                    autoComplete="cc-exp"
                    placeholder="12/29"
                  />
                  {fieldErrors['payment.expiry'] && (
                    <em className="field__error">{fieldErrors['payment.expiry']}</em>
                  )}
                </label>
                <label className="field">
                  <span>CVC</span>
                  <input
                    value={cvc}
                    onChange={(event) => setCvc(event.target.value.replace(/\D/g, '').slice(0, 4))}
                    required
                    autoComplete="cc-csc"
                    placeholder="123"
                  />
                  {fieldErrors['payment.cvc'] && (
                    <em className="field__error">{fieldErrors['payment.cvc']}</em>
                  )}
                </label>
              </div>
            </div>
          </section>
        </div>

        <aside className="summary-card summary-card--sticky">
          <h2>Your Order</h2>
          <ul className="summary-items">
            {items.map((item) => (
              <li key={`${item.id}-${item.size ?? ''}-${item.color ?? ''}`}>
                <span className="summary-items__tile">
                  {item.image_url ? (
                    <img src={item.image_url} alt="" loading="lazy" width={48} height={48} />
                  ) : (
                    item.emoji
                  )}
                </span>
                <span className="summary-items__name">
                  {item.name}
                  <small>× {item.quantity}</small>
                </span>
                <span>{money(item.price * item.quantity)}</span>
              </li>
            ))}
          </ul>

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

          <button type="submit" className="btn btn--primary btn--block btn--lg" disabled={submitting}>
            <ShoppingBag size={16} />
            {submitting ? 'Placing order…' : `Place test order — ${money(total)}`}
          </button>

          <p className="summary-card__note">
            <Lock size={13} /> Simulated payment · no card data leaves this demo.
          </p>
        </aside>
      </form>
    </div>
  );
}
