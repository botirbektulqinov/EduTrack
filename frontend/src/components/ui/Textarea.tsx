import { forwardRef, type TextareaHTMLAttributes } from 'react';
import styles from './Textarea.module.scss';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, id, className, ...rest }, ref) => {
    const textareaId = id ?? label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className={`${styles.group} ${className ?? ''}`}>
        {label && (
          <label htmlFor={textareaId} className={styles.label}>
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={`${styles.textarea} ${error ? styles.hasError : ''}`}
          rows={4}
          {...rest}
        />
        {error && <span className={styles.error}>{error}</span>}
      </div>
    );
  },
);

Textarea.displayName = 'Textarea';
export { Textarea };
export default Textarea;
