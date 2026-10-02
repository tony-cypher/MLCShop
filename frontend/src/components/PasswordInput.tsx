import { Eye, EyeOff } from 'lucide-react';
import { useId, useState } from 'react';

interface PasswordInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  autoComplete?: string;
  required?: boolean;
  minLength?: number;
}

/** Password field with a show/hide toggle. */
export default function PasswordInput({
  label,
  value,
  onChange,
  placeholder,
  autoComplete = 'current-password',
  required = false,
  minLength,
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const inputId = useId();

  return (
    <label className="field" htmlFor={inputId}>
      <span>{label}</span>
      <div className="field-password">
        <input
          id={inputId}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          title={visible ? 'Hide password' : 'Show password'}
        >
          {visible ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </div>
    </label>
  );
}
