import type { Question } from '@/types';
import s from './MCQSingleQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function MCQSingleQuestion({ question, value, onChange }: Props) {
  const selected = value as string | undefined;
  const options = question.options ?? [];

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <div className={s.options}>
        {options.map((opt) => (
          <label
            key={opt.id}
            className={`${s.option} ${selected === opt.id ? s.selected : ''}`}
          >
            <input
              type="radio"
              name={`q-${question.id}`}
              value={opt.id}
              checked={selected === opt.id}
              onChange={() => onChange(opt.id)}
              className={s.radio}
            />
            <span className={s.indicator} />
            <span className={s.label} dangerouslySetInnerHTML={{ __html: opt.content }} />
          </label>
        ))}
      </div>
    </div>
  );
}
