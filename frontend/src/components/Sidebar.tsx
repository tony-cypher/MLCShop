import { useEffect, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import type { Brand, PriceBounds } from '../types';

export interface SidebarFilters {
  minPrice: number | null;
  maxPrice: number | null;
  minRating: number | null;
  brands: string[];
  delivery: string | null;
}

interface SidebarProps {
  price: PriceBounds | null;
  histogram: number[];
  brands: Brand[];
  filters: SidebarFilters;
  onPriceChange: (min: number | null, max: number | null) => void;
  onRatingChange: (rating: number | null) => void;
  onBrandsChange: (brands: string[]) => void;
  onDeliveryChange: (delivery: string | null) => void;
}

const HIDDEN_BRANDS = 7; // reference image shows 7 rows + "More Brand"

export default function Sidebar({
  price,
  histogram,
  brands,
  filters,
  onPriceChange,
  onRatingChange,
  onBrandsChange,
  onDeliveryChange,
}: SidebarProps) {
  const [showAllBrands, setShowAllBrands] = useState(false);

  const bounds = price ?? { min: 0, max: 1000, avg: 0 };
  const [localMin, setLocalMin] = useState(bounds.min);
  const [localMax, setLocalMax] = useState(bounds.max);
  const draggingRef = useRef(false);
  const commitTimer = useRef<number | undefined>(undefined);

  // Adopt URL/prop values whenever they change from the outside (Reset, back button…)
  // but never while the user is dragging the slider.
  useEffect(() => {
    if (draggingRef.current) return;
    setLocalMin(filters.minPrice ?? bounds.min);
    setLocalMax(filters.maxPrice ?? bounds.max);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.minPrice, filters.maxPrice, bounds.min, bounds.max]);

  // Debounced commit so the product list does not refetch on every pixel.
  useEffect(() => {
    window.clearTimeout(commitTimer.current);
    commitTimer.current = window.setTimeout(() => {
      const min = localMin === bounds.min ? null : localMin;
      const max = localMax === bounds.max ? null : localMax;
      if (min !== (filters.minPrice ?? null) || max !== (filters.maxPrice ?? null)) {
        onPriceChange(min, max);
      }
    }, 350);
    return () => window.clearTimeout(commitTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [localMin, localMax, bounds.min, bounds.max]);

  const span = Math.max(1, bounds.max - bounds.min);
  const minPct = ((localMin - bounds.min) / span) * 100;
  const maxPct = ((localMax - bounds.min) / span) * 100;
  const histogramMax = Math.max(1, ...histogram);

  const visibleBrands = showAllBrands ? brands : brands.slice(0, HIDDEN_BRANDS);

  function toggleBrand(slug: string) {
    onBrandsChange(
      filters.brands.includes(slug)
        ? filters.brands.filter((brand) => brand !== slug)
        : [...filters.brands, slug],
    );
  }

  return (
    <aside className="sidebar">
      {/* ------------------------------------------------------------ Price */}
      <section className="side-card">
        <header className="side-card__head">
          <h3>Price Range</h3>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              setLocalMin(bounds.min);
              setLocalMax(bounds.max);
              onPriceChange(null, null);
            }}
          >
            Reset
          </button>
        </header>
        <p className="side-card__hint">The average price is ${bounds.avg}</p>

        <div className="price-range">
          <div className="price-range__chart" aria-hidden="true">
            {histogram.map((count, index) => (
              <span
                key={index}
                style={{ height: `${Math.max(8, (count / histogramMax) * 100)}%` }}
              />
            ))}
          </div>

          <div className="price-range__badges" aria-hidden="true">
            <span className="price-badge" style={{ left: `${minPct}%` }}>
              ${localMin}
            </span>
            <span className="price-badge" style={{ left: `${maxPct}%` }}>
              ${localMax}
            </span>
          </div>

          <div className="price-range__track">
            <div
              className="price-range__fill"
              style={{ left: `${minPct}%`, right: `${100 - maxPct}%` }}
            />
          </div>

          <input
            className="price-range__input"
            type="range"
            min={bounds.min}
            max={bounds.max}
            step={1}
            value={localMin}
            aria-label="Minimum price"
            onChange={(event) => {
              const value = Math.min(Number(event.target.value), localMax);
              setLocalMin(value);
            }}
            onPointerDown={() => (draggingRef.current = true)}
            onPointerUp={() => (draggingRef.current = false)}
            onKeyUp={() => (draggingRef.current = false)}
          />
          <input
            className="price-range__input"
            type="range"
            min={bounds.min}
            max={bounds.max}
            step={1}
            value={localMax}
            aria-label="Maximum price"
            onChange={(event) => {
              const value = Math.max(Number(event.target.value), localMin);
              setLocalMax(value);
            }}
            onPointerDown={() => (draggingRef.current = true)}
            onPointerUp={() => (draggingRef.current = false)}
            onKeyUp={() => (draggingRef.current = false)}
          />
        </div>
      </section>

      {/* --------------------------------------------------------- Star rating */}
      <section className="side-card">
        <header className="side-card__head">
          <h3>Star Rating</h3>
        </header>
        <div className="rating-filter">
          <div className="rating-filter__stars">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                className={`rating-filter__star ${
                  filters.minRating !== null && star <= filters.minRating ? 'is-on' : ''
                }`}
                onClick={() => onRatingChange(filters.minRating === star ? null : star)}
                aria-label={`${star} stars and up`}
              >
                ★
              </button>
            ))}
          </div>
          <span className="rating-filter__label">
            {filters.minRating ? `${filters.minRating} Stars & up` : 'Any rating'}
          </span>
        </div>
      </section>

      {/* -------------------------------------------------------------- Brand */}
      <section className="side-card">
        <header className="side-card__head">
          <h3>Brand</h3>
          <button type="button" className="link-button" onClick={() => onBrandsChange([])}>
            Reset
          </button>
        </header>

        <ul className="brand-list">
          {visibleBrands.map((brand) => {
            const checked = filters.brands.includes(brand.slug);
            return (
              <li key={brand.slug}>
                <label className="brand-row">
                  <span className="brand-row__left">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleBrand(brand.slug)}
                    />
                    <span className="brand-mark" style={{ background: brand.color }}>
                      {brand.initials}
                    </span>
                    {brand.name}
                  </span>
                  <span className={`fake-check ${checked ? 'is-checked' : ''}`}>
                    {checked && <Check size={12} strokeWidth={3} />}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>

        {brands.length > HIDDEN_BRANDS && (
          <button type="button" className="link-button link-button--block" onClick={() => setShowAllBrands((open) => !open)}>
            {showAllBrands ? 'Less Brand' : 'More Brand'}
          </button>
        )}
      </section>

      {/* ---------------------------------------------------- Delivery options */}
      <section className="side-card">
        <header className="side-card__head">
          <h3>Delivery Options</h3>
        </header>
        <div className="delivery-toggle">
          <button
            type="button"
            className={`delivery-toggle__btn ${filters.delivery === 'standard' ? 'is-active' : ''}`}
            onClick={() => onDeliveryChange(filters.delivery === 'standard' ? null : 'standard')}
          >
            Standard
          </button>
          <button
            type="button"
            className={`delivery-toggle__btn ${filters.delivery === 'pickup' ? 'is-active' : ''}`}
            onClick={() => onDeliveryChange(filters.delivery === 'pickup' ? null : 'pickup')}
          >
            Pick Up
          </button>
        </div>
      </section>
    </aside>
  );
}
