import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { CartItem, Product } from '../types';

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
  const [items, setItems] = useState<CartItem[]>(readCart);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items]);

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
    },
    [],
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
    },
    [],
  );

  const removeItem = useCallback(
    (productId: number, size?: string | null, color?: string | null) => {
      setItems((current) => current.filter((item) => !sameLine(item, productId, size, color)));
    },
    [],
  );

  const clear = useCallback(() => setItems([]), []);

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
