import { Heart } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { useAuth } from '../context/AuthContext';
import { useFavorites } from '../context/FavoritesContext';
import { api } from '../lib/api';
import type { Product, ProductsResponse } from '../types';

export default function FavoritesPage() {
  const { user } = useAuth();
  const { ids, localProducts } = useFavorites();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    if (!user) {
      setProducts(localProducts);
      setLoading(false);
      return;
    }

    setLoading(true);
    api<ProductsResponse>('/favorites')
      .then((response) => {
        if (!cancelled) setProducts(response.data);
      })
      .catch(() => {
        if (!cancelled) setProducts([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, ids]);

  return (
    <div className="favorites-page">
      <div className="page-head">
        <h1>Favourites</h1>
        <span className="muted">
          {loading ? '…' : `${products.length} saved`}
        </span>
      </div>

      {!user && (
        <div className="form-alert form-alert--info">
          Saved on this device only.{' '}
          <Link to="/login">Sign in</Link> to sync favourites across devices.
        </div>
      )}

      {loading ? (
        <div className="product-grid" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="p-card p-card--skeleton">
              <div className="skeleton skeleton--tile" />
              <div className="skeleton skeleton--title" />
              <div className="skeleton skeleton--pill" />
            </div>
          ))}
        </div>
      ) : products.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state__emoji">🤍</span>
          <h3>No favourites yet</h3>
          <p>Tap the heart on any product to save it here.</p>
          <Link to="/" className="btn btn--primary">
            <Heart size={15} /> Find something you love
          </Link>
        </div>
      ) : (
        <div className="product-grid">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
