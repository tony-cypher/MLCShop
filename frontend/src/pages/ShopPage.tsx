import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import CategoryPills from '../components/CategoryPills';
import ProductCard from '../components/ProductCard';
import Sidebar from '../components/Sidebar';
import type { SidebarFilters } from '../components/Sidebar';
import { api } from '../lib/api';
import type { Brand, Category, Product, ProductsMeta, ProductsResponse } from '../types';

const PER_PAGE = 12;

function buildQuery(params: URLSearchParams, page: number): string {
  const query = new URLSearchParams();
  params.forEach((value, key) => {
    if (key === 'brand') {
      query.append('brands[]', value);
    } else if (key === 'q') {
      if (value) query.set('search', value);
    } else {
      query.set(key, value);
    }
  });
  query.set('per_page', String(PER_PAGE));
  query.set('page', String(page));
  // Merchandising default: featured picks first, then best rated.
  if (!query.has('sort')) query.set('sort', 'featured');
  return query.toString();
}

function toNumber(value: string | null): number | null {
  if (value === null || value === '') return null;
  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? null : parsed;
}

export default function ShopPage() {
  const [params, setParams] = useSearchParams();

  const [categories, setCategories] = useState<Category[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [meta, setMeta] = useState<ProductsMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    void (async () => {
      try {
        const [categoryRes, brandRes] = await Promise.all([
          api<{ data: Category[] }>('/categories'),
          api<{ data: Brand[] }>('/brands'),
        ]);
        setCategories(categoryRes.data);
        setBrands(brandRes.data);
      } catch {
        // The grid still works without the sidebar extras.
      }
    })();
  }, []);

  const queryKey = params.toString();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api<ProductsResponse>(`/products?${buildQuery(params, 1)}`)
      .then((response) => {
        if (cancelled) return;
        setProducts(response.data);
        setMeta(response.meta);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(caught instanceof Error ? caught.message : 'Could not load products.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryKey, retryKey]);

  async function loadMore() {
    if (!meta) return;
    setLoadingMore(true);
    try {
      const response = await api<ProductsResponse>(
        `/products?${buildQuery(params, meta.current_page + 1)}`,
      );
      setProducts((current) => [...current, ...response.data]);
      setMeta(response.meta);
    } catch {
      // keep list as-is
    } finally {
      setLoadingMore(false);
    }
  }

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params);
    if (value === null) next.delete(key);
    else next.set(key, value);
    next.delete('page');
    setParams(next, { replace: true });
  }

  function setMultiBrand(values: string[]) {
    const next = new URLSearchParams(params);
    next.delete('brand');
    values.forEach((slug) => next.append('brand', slug));
    next.delete('page');
    setParams(next, { replace: true });
  }

  const activePill =
    params.get('deals') === '1' ? 'deals' : params.get('category') ?? 'all';

  function selectPill(value: string) {
    const next = new URLSearchParams(params);
    next.delete('page');
    next.delete('deals');
    next.delete('category');
    if (value === 'deals') next.set('deals', '1');
    else if (value !== 'all') next.set('category', value);
    setParams(next, { replace: true });
  }

  const filters: SidebarFilters = {
    minPrice: toNumber(params.get('min_price')),
    maxPrice: toNumber(params.get('max_price')),
    minRating: toNumber(params.get('min_rating')),
    brands: params.getAll('brand'),
    delivery: params.get('delivery'),
  };

  const hasMore = meta ? meta.current_page < meta.last_page : false;

  return (
    <div className="shop">
      <CategoryPills
        categories={categories}
        active={activePill}
        dealsCount={meta?.deals_count}
        onSelect={selectPill}
      />

      <div className="shop__body">
        <Sidebar
          price={meta?.price ?? null}
          histogram={meta?.price_histogram ?? []}
          brands={brands}
          filters={filters}
          onPriceChange={(min, max) => {
            const next = new URLSearchParams(params);
            next.delete('page');
            if (min === null) next.delete('min_price');
            else next.set('min_price', String(min));
            if (max === null) next.delete('max_price');
            else next.set('max_price', String(max));
            setParams(next, { replace: true });
          }}
          onRatingChange={(rating) => setParam('min_rating', rating === null ? null : String(rating))}
          onBrandsChange={setMultiBrand}
          onDeliveryChange={(delivery) => setParam('delivery', delivery)}
        />

        <div className="shop__results">
          {!loading && !error && products.length > 0 && (
            <div className="results-bar">
              <span className="results-bar__count">
                Showing <strong>{products.length}</strong> of <strong>{meta?.total ?? products.length}</strong>{' '}
                {(meta?.total ?? products.length) === 1 ? 'product' : 'products'}
              </span>

              <label className="sort-select">
                <span>Sort by</span>
                <select
                  value={params.get('sort') ?? 'featured'}
                  onChange={(event) =>
                    setParam('sort', event.target.value === 'featured' ? null : event.target.value)
                  }
                >
                  <option value="featured">Featured</option>
                  <option value="newest">Newest</option>
                  <option value="rating">Top rated</option>
                  <option value="price_asc">Price: low to high</option>
                  <option value="price_desc">Price: high to low</option>
                </select>
              </label>
            </div>
          )}

          {loading ? (
            <div className="product-grid" aria-hidden="true">
              {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="p-card p-card--skeleton">
                  <div className="skeleton skeleton--tile" />
                  <div className="skeleton skeleton--title" />
                  <div className="skeleton skeleton--pill" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="empty-state">
              <span className="empty-state__emoji">📡</span>
              <h3>Cannot reach the shop API</h3>
              <p>{error}</p>
              <p className="empty-state__hint">
                Is the API server running? <code>cd backend && uvicorn app.main:app --reload</code>
              </p>
              <button type="button" className="btn btn--primary" onClick={() => setRetryKey((key) => key + 1)}>
                Retry
              </button>
            </div>
          ) : products.length === 0 ? (
            <div className="empty-state">
              <span className="empty-state__emoji">🔍</span>
              <h3>No products match those filters</h3>
              <p>Try a wider price range, fewer brands, or a different category.</p>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => setParams({}, { replace: true })}
              >
                Clear all filters
              </button>
            </div>
          ) : (
            <>
              <div className="product-grid">
                {products.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>

              {hasMore && (
                <div className="load-more">
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={loadingMore}
                    onClick={() => void loadMore()}
                  >
                    {loadingMore ? 'Loading…' : 'Load more products'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
