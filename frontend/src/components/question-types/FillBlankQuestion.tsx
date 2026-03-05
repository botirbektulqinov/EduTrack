import { useMemo } from 'react';
import type { Question } from '@/types';
import s from './FillBlankQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function FillBlankQuestion({ question, value, onChange }: Props) {
  const answers = (value as string[] | undefined) ?? [];

  const parts = useMemo(() => question.content.split(/___/g), [question.content]);
  const blankCount = parts.length - 1;

  const handleChange = (index: number, val: string) => {
    const next = [...answers];
    while (next.length < blankCount) next.push('');
    next[index] = val;
    onChange(next);
  };

  return (
    <div className={s.wrapper}>
      <div className={s.sentence}>
        {parts.map((part, i) => (
          <span key={i}>
            <span dangerouslySetInnerHTML={{ __html: part }} />
            {i < blankCount && (
              <input
                type="text"
                className={s.blank}
                value={answers[i] ?? ''}
                onChange={(e) => handleChange(i, e.target.value)}
                placeholder={`blank ${i + 1}`}
                autoComplete="off"
              />
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
