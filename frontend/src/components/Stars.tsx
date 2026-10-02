import { Star } from 'lucide-react';

interface StarsProps {
  value: number;
  size?: number;
  className?: string;
}

/** Read-only star rating (fractional values fill the last star). */
export default function Stars({ value, size = 14, className = '' }: StarsProps) {
  const full = Math.round(value);

  return (
    <span className={`stars ${className}`} aria-label={`${value} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((index) => (
        <Star
          key={index}
          size={size}
          className={index <= full ? 'stars__on' : 'stars__off'}
          fill={index <= full ? 'currentColor' : 'none'}
          strokeWidth={2}
        />
      ))}
    </span>
  );
}
