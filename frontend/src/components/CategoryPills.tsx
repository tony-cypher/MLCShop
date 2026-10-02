import type { Category } from '../types';

interface CategoryPillsProps {
  categories: Category[];
  active: string; // 'all' | 'deals' | category slug
  dealsCount?: number;
  onSelect: (value: string) => void;
}

export default function CategoryPills({ categories, active, dealsCount, onSelect }: CategoryPillsProps) {
  const pills = [
    { value: 'all', label: 'All Categories' },
    { value: 'deals', label: dealsCount ? `Deals (${dealsCount})` : 'Deals' },
    ...categories.map((category) => ({ value: category.slug, label: category.name })),
  ];

  return (
    <div className="pills" role="tablist" aria-label="Categories">
      {pills.map((pill) => (
        <button
          key={pill.value}
          type="button"
          role="tab"
          aria-selected={active === pill.value}
          className={`pill ${active === pill.value ? 'pill--active' : ''}`}
          onClick={() => onSelect(pill.value)}
        >
          {pill.label}
        </button>
      ))}
    </div>
  );
}
