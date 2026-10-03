import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../lib/api';
import type { CartItem, Product } from '../types';
import { useAuth } from './AuthContext';

const STORAGE_KEY = 'mlc_cart';

interface CartContextValue {
  items: CartItem[];
  count: number;
  subtotal: number;
  addItem: (product: Product, quantity?: number, size?: string | null, color?: string | null) => void;
  setQuantity: (productId: number, quantity: number, size?: string | null, color?: string | null) => void;
  removeItem: (productId: number, size?: string | null, color?: string | null) => void;
  clear: () => void;
}

const CartContext = createContext<CartContextValue | null>(null);

function readCart(): CartItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as CartItem[]) : [];
  } catch {
    return [];
  }
}

function sameLine(item: CartItem, id: number, size?: string | null, color?: string | null) {
  return item.id === id && (item.size ?? null) === (size ?? null) && (item.color ?? null) === (color ?? null);
}

export function CartProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [items, setItems] = useState<CartItem[]>(readCart);
  const isSyncingRef = useRef(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items]);

  // Sync with cloud backend whenever user logs in or every 4 seconds to catch mobile changes instantly
  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    const fetchServerCart = async () => {
      if (isSyncingRef.current) return;
      try {
        const res = await api<{ data: CartItem[] }>('/cart');
        if (!cancelled && res.data) {
          setItems(res.data);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(res.data));
        }
      } catch {
        // Fall back to local storage
      }
    };

    // First, merge any existing local items if logging in for the first time
    const initialMerge = async () => {
      const local = readCart();
      if (local.length > 0) {
        try {
          isSyncingRef.current = true;
          const res = await api<{ data: CartItem[] }>('/cart/sync', {
            method: 'POST',
            body: {
              items: local.map((i) => ({
                id: i.id,
                quantity: i.quantity,
                size: i.size,
                color: i.color,
              })),
            },
          });
          if (!cancelled && res.data) {
            setItems(res.data);
            localStorage.setItem(STORAGE_KEY, JSON.stringify(res.data));
          }
        } catch {
          await fetchServerCart();
        } finally {
          isSyncingRef.current = false;
        }
      } else {
        await fetchServerCart();
      }
    };

    void initialMerge();

    // Poll server cart every 3.5 seconds so additions from mobile appear instantly on web
    const interval = setInterval(() => {
      void fetchServerCart();
    }, 3500);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [user]);

  const addItem = useCallback(
    (product: Product, quantity = 1, size?: string | null, color?: string | null) => {
      setItems((current) => {
        const existing = current.find((item) => sameLine(item, product.id, size, color));
        if (existing) {
          return current.map((item) =>
            sameLine(item, product.id, size, color)
              ? { ...item, quantity: Math.min(item.stock, item.quantity + quantity) }
              : item,
          );
        }
        return [
          ...current,
          {
            id: product.id,
            slug: product.slug,
            name: product.name,
            price: Number.parseFloat(product.price),
            compare_at_price: product.compare_at_price
              ? Number.parseFloat(product.compare_at_price)
              : null,
            emoji: product.emoji,
            image_url: product.image_url,
            quantity,
            size: size ?? null,
            color: color ?? null,
            stock: product.stock,
            delivery_standard: product.delivery_standard,
            delivery_pickup: product.delivery_pickup,
          },
        ];
      });

      if (user) {
        void api<{ data: CartItem[] }>('/cart', {
          method: 'POST',
          body: {
            product_id: product.id,
            quantity,
            size: size ?? null,
            color: color ?? null,
          },
        }).then((res) => {
          if (res.data) setItems(res.data);
        }).catch(() => {});
      }
    },
    [user],
  );

  const setQuantity = useCallback(
    (productId: number, quantity: number, size?: string | null, color?: string | null) => {
      setItems((current) =>
        current.map((item) =>
          sameLine(item, productId, size, color)
            ? { ...item, quantity: Math.max(1, Math.min(item.stock, quantity)) }
            : item,
        ),
      );

      if (user) {
        void api<{ data: CartItem[] }>('/cart', {
          method: 'PUT',
          body: {
            product_id: productId,
            quantity,
            size: size ?? null,
            color: color ?? null,
          },
        }).then((res) => {
          if (res.data) setItems(res.data);
        }).catch(() => {});
      }
    },
    [user],
  );

  const removeItem = useCallback(
    (productId: number, size?: string | null, color?: string | null) => {
      setItems((current) => current.filter((item) => !sameLine(item, productId, size, color)));

      if (user) {
        const query = new URLSearchParams({ product_id: String(productId) });
        if (size) query.set('size', size);
        if (color) query.set('color', color);
        void api<{ data: CartItem[] }>(`/cart?${query.toString()}`, {
          method: 'DELETE',
        }).then((res) => {
          if (res.data) setItems(res.data);
        }).catch(() => {});
      }
    },
    [user],
  );

  const clear = useCallback(() => {
    setItems([]);
    if (user) {
      void api<{ data: CartItem[] }>('/cart/clear', {
        method: 'DELETE',
      }).catch(() => {});
    }
  }, [user]);

  const count = useMemo(() => items.reduce((sum, item) => sum + item.quantity, 0), [items]);
  const subtotal = useMemo(
    () => items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [items],
  );

  const value = useMemo(
    () => ({ items, count, subtotal, addItem, setQuantity, removeItem, clear }),
    [items, count, subtotal, addItem, setQuantity, removeItem, clear],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const context = useContext(CartContext);
  if (!context) throw new Error('useCart must be used inside CartProvider');
  return context;
}
