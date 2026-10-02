import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../lib/api';
import type { Product, ProductsResponse } from '../types';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

const STORAGE_KEY = 'mlc_favorites';

interface FavoritesContextValue {
  ids: Set<number>;
  /** Full product records saved while signed out (guest fallback). */
  localProducts: Product[];
  has: (productId: number) => boolean;
  toggle: (product: Product) => Promise<void>;
}

const FavoritesContext = createContext<FavoritesContextValue | null>(null);

function readLocalProducts(): Product[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Older payloads stored plain ids — drop those.
    return parsed.filter((entry): entry is Product => typeof entry === 'object' && entry !== null && 'id' in entry);
  } catch {
    return [];
  }
}

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { push } = useToast();
  const [localProducts, setLocalProducts] = useState<Product[]>(readLocalProducts);
  const [serverIds, setServerIds] = useState<Set<number>>(() => new Set());

  const ids = useMemo(() => {
    const merged = new Set(serverIds);
    for (const product of localProducts) merged.add(product.id);
    return merged;
  }, [serverIds, localProducts]);

  // Signed-in users also see picks made while signed out.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    (async () => {
      try {
        const response = await api<ProductsResponse>('/favorites');
        if (!cancelled) setServerIds(new Set(response.data.map((product) => product.id)));
      } catch {
        // Keep the merged view if the request fails.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [user]);

  const has = useCallback((productId: number) => ids.has(productId), [ids]);

  const persistLocal = useCallback((next: Product[]) => {
    setLocalProducts(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const toggle = useCallback(
    async (product: Product) => {
      const isFavorite = ids.has(product.id);

      if (user) {
        try {
          const response = await api<{ data: number[] }>(`/favorites/${product.id}`, {
            method: isFavorite ? 'DELETE' : 'POST',
          });
          setServerIds(new Set(response.data));
        } catch {
          push('Could not update favourites. Please try again.', 'error');
          return;
        }
        // Keep the local mirror fresh too, so signed-out mode stays rich.
        const localNext = isFavorite
          ? localProducts.filter((item) => item.id !== product.id)
          : [...localProducts.filter((item) => item.id !== product.id), product];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(localNext));
        setLocalProducts(localNext);
      } else {
        persistLocal(
          isFavorite
            ? localProducts.filter((item) => item.id !== product.id)
            : [...localProducts.filter((item) => item.id !== product.id), product],
        );
      }

      push(
        isFavorite ? 'Removed from favourites' : `Saved “${product.name}” to favourites`,
        isFavorite ? 'info' : 'success',
      );
    },
    [user, ids, localProducts, persistLocal, push],
  );

  const value = useMemo(() => ({ ids, localProducts, has, toggle }), [ids, localProducts, has, toggle]);

  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>;
}

export function useFavorites(): FavoritesContextValue {
  const context = useContext(FavoritesContext);
  if (!context) throw new Error('useFavorites must be used inside FavoritesProvider');
  return context;
}
