import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Heart, LogOut, Moon, Package, Search, ShoppingBag, Sun, UserRound } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useTheme } from '../context/ThemeContext';
import { initialsOf } from '../lib/format';

export default function Header() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [query, setQuery] = useState(() => {
    return location.pathname === '/' ? new URLSearchParams(location.search).get('q') ?? '' : '';
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Keep the search box in sync when the shop URL changes.
  useEffect(() => {
    if (location.pathname === '/') {
      setQuery(new URLSearchParams(location.search).get('q') ?? '');
    }
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [menuOpen]);

  function onSearch(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams(location.pathname === '/' ? location.search : '');
    if (query.trim()) params.set('q', query.trim());
    else params.delete('q');
    params.delete('page');
    navigate(`/?${params.toString()}`);
  }

  return (
    <header className="header">
      <div className="header__inner">
        <Link to="/" className="logo" aria-label="MLC home">
          <span className="logo__mark">M</span>
          <span className="logo__text">MLC</span>
        </Link>

        <form className="search" onSubmit={onSearch} role="search">
          <Search size={17} className="search__icon" />
          <input
            type="search"
            placeholder="Search products, brands and categories"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search products"
          />
        </form>

        <nav className="header__actions">
          <Link to="/orders" className="header__link">
            <Package size={18} />
            <span>Orders</span>
          </Link>
          <Link to="/favourites" className="header__link">
            <Heart size={18} />
            <span>Favourites</span>
          </Link>
          <Link to="/cart" className="header__link header__link--cart">
            <span className="header__cart-icon">
              <ShoppingBag size={18} />
              {count > 0 && <span className="cart-badge">{count > 9 ? '9+' : count}</span>}
            </span>
            <span>Cart</span>
          </Link>

          <span className="header__divider" aria-hidden="true" />

          <button
            type="button"
            className="icon-button"
            onClick={toggleTheme}
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            title={theme === 'light' ? 'Dark mode' : 'Light mode'}
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>

          {user ? (
            <div className="avatar-menu" ref={menuRef}>
            <button
              type="button"
              className="avatar"
              onClick={() => setMenuOpen((open) => !open)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-label="Account menu"
            >
              {user.avatar_url ? (
                <img
                  className="avatar__img"
                  src={user.avatar_url}
                  alt=""
                  referrerPolicy="no-referrer"
                />
              ) : (
                initialsOf(user.name)
              )}
            </button>
              {menuOpen && (
                <div className="avatar-menu__dropdown" role="menu">
                  <div className="avatar-menu__head">
                    <strong>{user.name}</strong>
                    <small>{user.email}</small>
                  </div>
                  <Link to="/orders" role="menuitem" onClick={() => setMenuOpen(false)}>
                    <Package size={15} /> Orders
                  </Link>
                  <Link to="/favourites" role="menuitem" onClick={() => setMenuOpen(false)}>
                    <Heart size={15} /> Favourites
                  </Link>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false);
                      void logout();
                      navigate('/');
                    }}
                  >
                    <LogOut size={15} /> Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link to="/login" className="signin-btn">
              <UserRound size={16} />
              <span>Sign in</span>
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
