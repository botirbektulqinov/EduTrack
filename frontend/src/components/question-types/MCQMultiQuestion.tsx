import type { Question } from '@/types';
import s from './MCQMultiQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function MCQMultiQuestion({ question, value, onChange }: Props) {
  const selected = (value as string[] | undefined) ?? [];
  const options = question.options ?? [];

  const toggle = (optId: string) => {
    const next = selected.includes(optId)
      ? selected.filter((id) => id !== optId)
      : [...selected, optId];
    onChange(next);
  };

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <p className={s.hint}>Select all that apply</p>
      <div className={s.options}>
        {options.map((opt) => {
          const checked = selected.includes(opt.id);
          return (
            <label
              key={opt.id}
              className={`${s.option} ${checked ? s.selected : ''}`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggle(opt.id)}
                className={s.checkbox}
              />
              <span className={s.indicator}>
                {checked && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </span>
              <span className={s.label} dangerouslySetInnerHTML={{ __html: opt.content }} />
            </label>
          );
        })}
      </div>
    </div>
  );
}
