import { ArrowLeft, Heart, Minus, Plus, PackageX, Store, Truck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import Stars from '../components/Stars';
import { useCart } from '../context/CartContext';
import { useFavorites } from '../context/FavoritesContext';
import { useToast } from '../context/ToastContext';
import { api } from '../lib/api';
import { money, shortDate } from '../lib/format';
import type { ProductDetailResponse } from '../types';

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>();
  const [detail, setDetail] = useState<ProductDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [quantity, setQuantity] = useState(1);
  const [size, setSize] = useState<string | null>(null);
  const [color, setColor] = useState<string | null>(null);

  const { addItem } = useCart();
  const { has, toggle } = useFavorites();
  const { push } = useToast();

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setQuantity(1);

    api<ProductDetailResponse>(`/products/${slug}`)
      .then((response) => {
        if (cancelled) return;
        setDetail(response);
        setSize(response.data.options?.sizes?.[0] ?? null);
        setColor(response.data.options?.colors?.[0] ?? null);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Product not found.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (loading) {
    return (
      <div className="product-page">
        <div className="product-hero">
          <div className="skeleton skeleton--hero" />
          <div className="product-hero__info">
            <div className="skeleton skeleton--title" />
            <div className="skeleton skeleton--title" />
            <div className="skeleton skeleton--pill" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="empty-state">
        <span className="empty-state__emoji">🫥</span>
        <h3>Product not found</h3>
        <p>{error}</p>
        <Link to="/" className="btn btn--primary">
          Back to shop
        </Link>
      </div>
    );
  }

  const product = detail.data;
  const favourite = has(product.id);
  const sale = product.compare_at_price !== null;
  const discount = sale
    ? Math.round((1 - Number(product.price) / Number(product.compare_at_price)) * 100)
    : 0;
  const sizes = product.options?.sizes ?? [];
  const colors = product.options?.colors ?? [];

  function addToCart() {
    if (sizes.length > 0 && !size) {
      push('Please choose a size first', 'error');
      return;
    }
    if (colors.length > 0 && !color) {
      push('Please choose a colour first', 'error');
      return;
    }
    addItem(product, quantity, size, color);
    push(`“${product.name}” added to cart`, 'success');
  }

  return (
    <div className="product-page">
      <Link to="/" className="back-link">
        <ArrowLeft size={15} /> Back to shop
      </Link>

      <div className="product-hero">
        <div className={`product-hero__tile ${product.featured ? 'is-featured' : ''}`}>
          {product.badge === 'top' && <span className="badge badge--top">Top Item</span>}
          {sale && <span className="badge badge--sale">- {discount}%</span>}
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} />
          ) : (
            <span className="product-hero__emoji">{product.emoji}</span>
          )}
          <button
            type="button"
            className={`heart-btn heart-btn--lg ${favourite ? 'is-on' : ''}`}
            onClick={() => void toggle(product)}
            aria-label={favourite ? 'Remove from favourites' : 'Add to favourites'}
          >
            <Heart size={18} fill={favourite ? 'currentColor' : 'none'} />
          </button>
        </div>

        <div className="product-hero__info">
          <div className="chip-row">
            {product.category && (
              <Link to={`/?category=${product.category.slug}`} className="chip">
                {product.category.emoji} {product.category.name}
              </Link>
            )}
            {product.brand && <span className="chip chip--brand">{product.brand.name}</span>}
            {product.is_deal && <span className="chip chip--deal">Deal</span>}
          </div>

          <h1 className="product-hero__title">{product.name}</h1>

          <div className="rating-line">
            <Stars value={Number(product.rating)} size={16} />
            <strong>{Number(product.rating).toFixed(1)}</strong>
            <span>{product.reviews_count} reviews</span>
          </div>

          <div className="product-price">
            <span className="product-price__current">{money(product.price)}</span>
            {sale && (
              <>
                <s>{money(product.compare_at_price!)}</s>
                <span className="product-price__save">Save {money(Number(product.compare_at_price) - Number(product.price))}</span>
              </>
            )}
          </div>

          {product.description && <p className="product-hero__desc">{product.description}</p>}

          <div className="delivery-notes">
            {product.delivery_standard && (
              <span>
                <Truck size={15} /> Standard delivery — free over $100
              </span>
            )}
            {product.delivery_pickup && (
              <span>
                <Store size={15} /> Pick up available
              </span>
            )}
          </div>

          {sizes.length > 0 && (
            <div className="option-group">
              <span className="option-group__label">Size</span>
              <div className="option-pills">
                {sizes.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={`option-pill ${size === option ? 'is-active' : ''}`}
                    onClick={() => setSize(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          )}

          {colors.length > 0 && (
            <div className="option-group">
              <span className="option-group__label">Colour</span>
              <div className="option-pills">
                {colors.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={`option-pill ${color === option ? 'is-active' : ''}`}
                    onClick={() => setColor(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="buy-row">
            <div className="qty-stepper">
              <button
                type="button"
                onClick={() => setQuantity((current) => Math.max(1, current - 1))}
                aria-label="Decrease quantity"
              >
                <Minus size={15} />
              </button>
              <span>{quantity}</span>
              <button
                type="button"
                onClick={() => setQuantity((current) => Math.min(product.stock, current + 1))}
                aria-label="Increase quantity"
              >
                <Plus size={15} />
              </button>
            </div>

            <button
              type="button"
              className="btn btn--primary btn--lg"
              disabled={product.stock === 0}
              onClick={addToCart}
            >
              {product.stock === 0 ? 'Out of stock' : 'Add to cart'}
            </button>

            <button
              type="button"
              className={`btn btn--outline btn--lg ${favourite ? 'is-on' : ''}`}
              onClick={() => void toggle(product)}
            >
              <Heart size={16} fill={favourite ? 'currentColor' : 'none'} />
              {favourite ? 'Saved' : 'Favourite'}
            </button>
          </div>

          <p className="stock-note">
            {product.stock > 0 ? (
              <>
                <strong>In stock</strong> — {product.stock} available
                {product.stock <= 10 ? ` · Only ${product.stock} left!` : ''}
              </>
            ) : (
              <>
                <PackageX size={14} /> Out of stock
              </>
            )}
          </p>
        </div>
      </div>

      <section className="reviews">
        <div className="reviews__head">
          <h2>Customer Reviews</h2>
          <div className="reviews__summary">
            <strong>{Number(product.rating).toFixed(1)}</strong>
            <Stars value={Number(product.rating)} size={16} />
            <span>{product.reviews_count} reviews</span>
          </div>
        </div>

        {detail.reviews.length === 0 ? (
          <p className="muted">No written reviews yet — be the first.</p>
        ) : (
          <ul className="reviews__list">
            {detail.reviews.map((review) => (
              <li key={review.id} className="review">
                <span className="review__avatar">{review.avatar}</span>
                <div className="review__body">
                  <div className="review__meta">
                    <strong>{review.author}</strong>
                    <Stars value={review.rating} size={13} />
                    <time>{shortDate(review.created_at)}</time>
                  </div>
                  {review.comment && <p>{review.comment}</p>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {detail.related.length > 0 && (
        <section className="related">
          <h2>You may also like</h2>
          <div className="product-grid">
            {detail.related.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
