export interface Category {
  id: number;
  name: string;
  slug: string;
  emoji: string | null;
}

export interface Brand {
  id: number;
  name: string;
  slug: string;
  initials: string;
  color: string;
}

export interface ProductOptions {
  sizes?: string[];
  colors?: string[];
}

export interface Product {
  id: number;
  category_id: number;
  brand_id: number | null;
  name: string;
  slug: string;
  description: string | null;
  price: string;
  compare_at_price: string | null;
  emoji: string;
  image_url: string | null;
  badge: string | null;
  featured: boolean;
  is_deal: boolean;
  rating: string;
  reviews_count: number;
  rating_chips: number[] | null;
  options: ProductOptions | null;
  delivery_standard: boolean;
  delivery_pickup: boolean;
  stock: number;
  created_at?: string;
  category?: Category;
  brand?: Brand | null;
}

export interface PriceBounds {
  min: number;
  max: number;
  avg: number;
}

export interface ProductsMeta {
  current_page: number;
  per_page: number;
  total: number;
  last_page: number;
  price: PriceBounds;
  price_histogram: number[];
  deals_count: number;
}

export interface ProductsResponse {
  data: Product[];
  meta: ProductsMeta;
}

export interface ProductDetailResponse {
  data: Product;
  reviews: Review[];
  related: Product[];
}

export interface User {
  id: number;
  name: string;
  email: string;
  email_verified_at: string | null;
  avatar_emoji?: string;
  avatar_url?: string | null;
}

export interface AuthResponse {
  data: User;
  token?: string;
  message?: string;
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
  passwordConfirmation: string;
}

export interface Review {
  id: number;
  author: string;
  avatar: string;
  rating: number;
  comment: string | null;
  created_at: string | null;
}

export interface OrderItem {
  id: number;
  product_id: number | null;
  name: string;
  emoji: string | null;
  image_url: string | null;
  price: string;
  quantity: number;
}

export interface Order {
  id: number;
  reference: string;
  user_id: number | null;
  email: string;
  name: string;
  phone: string | null;
  status: string;
  payment_status: string;
  payment_method: string;
  card_last4: string | null;
  delivery_method: string;
  subtotal: string;
  shipping: string;
  total: string;
  address: Record<string, string> | null;
  placed_at: string | null;
  items: OrderItem[];
}

export interface CartItem {
  id: number;
  slug: string;
  name: string;
  price: number;
  compare_at_price: number | null;
  emoji: string;
  image_url: string | null;
  quantity: number;
  size: string | null;
  color: string | null;
  stock: number;
  delivery_standard: boolean;
  delivery_pickup: boolean;
}

export type Theme = 'light' | 'dark';

export type DeliveryMethod = 'standard' | 'pickup';
