import { forwardRef, type InputHTMLAttributes } from 'react';
import styles from './Input.module.scss';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, id, className, ...rest }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className={`${styles.group} ${className ?? ''}`}>
        {label && (
          <label htmlFor={inputId} className={styles.label}>
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`${styles.input} ${error ? styles.hasError : ''}`}
          {...rest}
        />
        {error && <span className={styles.error}>{error}</span>}
        {!error && helperText && (
          <span className={styles.helper}>{helperText}</span>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';
export { Input };
export default Input;
