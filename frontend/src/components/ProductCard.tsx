import { Heart, ShoppingBag } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useFavorites } from '../context/FavoritesContext';
import { useToast } from '../context/ToastContext';
import { money } from '../lib/format';
import type { Product } from '../types';
import Stars from './Stars';

const CHIP_AVATARS = ['👩🏽', '🧑🏻', '👩🏼', '🧑🏿', '👨🏻'];

function HeartButton({ product }: { product: Product }) {
  const { has, toggle } = useFavorites();
  const filled = has(product.id);

  return (
    <button
      type="button"
      className={`heart-btn ${filled ? 'is-on' : ''}`}
      aria-label={filled ? 'Remove from favourites' : 'Add to favourites'}
      onClick={() => void toggle(product)}
    >
      <Heart size={16} fill={filled ? 'currentColor' : 'none'} />
    </button>
  );
}

/** Quick add appears on hover — direct add when there is nothing to choose. */
function QuickAdd({ product }: { product: Product }) {
  const { addItem } = useCart();
  const { push } = useToast();

  const needsOptions =
    (product.options?.sizes?.length ?? 0) > 0 || (product.options?.colors?.length ?? 0) > 0;

  if (needsOptions) {
    return (
      <Link to={`/product/${product.slug}`} className="quick-add quick-add--ghost">
        Choose options
      </Link>
    );
  }

  return (
    <button
      type="button"
      className="quick-add"
      onClick={() => {
        addItem(product, 1);
        push(`“${product.name}” added to cart`, 'success');
      }}
    >
      <ShoppingBag size={15} />
      Add to cart
    </button>
  );
}

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const sale = product.compare_at_price !== null;
  const featured = product.featured;
  const savings = sale ? Number(product.compare_at_price) - Number(product.price) : 0;

  return (
    <article className={`p-card ${featured ? 'p-card--featured' : ''}`}>
      <div className="p-card__media">
        <Link
          to={`/product/${product.slug}`}
          className="p-card__media-link"
          aria-label={product.name}
        >
          <div className="p-card__tile">
            {product.image_url ? (
              <img src={product.image_url} alt="" loading="lazy" />
            ) : (
              <span className="p-card__emoji">{product.emoji}</span>
            )}

            {featured && product.rating_chips && (
              <>
                <span className="rating-chip rating-chip--one">
                  <span className="rating-chip__avatar">{CHIP_AVATARS[0]}</span>
                  {product.rating_chips[0]?.toFixed(1)}/5
                  <span className="rating-chip__star">★</span>
                </span>
                {product.rating_chips[1] !== undefined && (
                  <span className="rating-chip rating-chip--two">
                    <span className="rating-chip__avatar">{CHIP_AVATARS[1]}</span>
                    {product.rating_chips[1].toFixed(1)}/5
                    <span className="rating-chip__star">★</span>
                  </span>
                )}
                {product.rating_chips[2] !== undefined && (
                  <span className="rating-chip rating-chip--three">
                    <span className="rating-chip__avatar">{CHIP_AVATARS[2]}</span>
                    {product.rating_chips[2].toFixed(1)}/5
                    <span className="rating-chip__star">★</span>
                  </span>
                )}
              </>
            )}
          </div>
        </Link>

        <div className="p-card__overlay">
          <HeartButton product={product} />
        </div>

        <div className="p-card__quick">
          <QuickAdd product={product} />
        </div>
      </div>

      <div className="p-card__body">
        <Link to={`/product/${product.slug}`} className="p-card__body-link">
          {!featured && product.badge === 'top' && (
            <span className="badge badge--top">Top Item</span>
          )}

          <h3 className="p-card__title">{product.name}</h3>

          <div className="price-row">
            <span className="price-now">{money(product.price)}</span>
            {sale && <s className="price-old">{money(product.compare_at_price!)}</s>}
            {sale && savings >= 1 && <span className="save-chip">Save {money(savings)}</span>}
          </div>
        </Link>

        <div className="p-card__meta">
          <span className="p-card__rating-line">
            <Stars value={Number(product.rating)} size={13} />
            <strong>{Number(product.rating).toFixed(1)}</strong>
            <span>({product.reviews_count})</span>
          </span>
          {product.brand && <span className="p-card__brand">{product.brand.name}</span>}
        </div>
      </div>
    </article>
  );
}
