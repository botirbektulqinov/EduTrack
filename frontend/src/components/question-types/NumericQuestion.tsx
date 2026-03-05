import type { Question } from '@/types';
import s from './NumericQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function NumericQuestion({ question, value, onChange }: Props) {
  const current = value as number | null | undefined;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    if (raw === '') {
      onChange(null);
      return;
    }
    const num = parseFloat(raw);
    if (!isNaN(num)) onChange(num);
  };

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <div className={s.inputGroup}>
        <input
          type="number"
          className={s.input}
          value={current ?? ''}
          onChange={handleChange}
          placeholder="Enter a number"
          step="any"
        />
      </div>
    </div>
  );
}
