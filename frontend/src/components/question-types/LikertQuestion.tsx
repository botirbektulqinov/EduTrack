import type { Question } from '@/types';
import s from './LikertQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

const DEFAULT_SCALE = [
  { value: '1', label: 'Strongly Disagree' },
  { value: '2', label: 'Disagree' },
  { value: '3', label: 'Neutral' },
  { value: '4', label: 'Agree' },
  { value: '5', label: 'Strongly Agree' },
];

export function LikertQuestion({ question, value, onChange }: Props) {
  const selected = value as string | undefined;
  const options = question.options;

  const scale = options && options.length > 0
    ? options.map((opt) => ({ value: opt.id, label: opt.content }))
    : DEFAULT_SCALE;

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <div className={s.scale}>
        {scale.map((item) => (
          <label
            key={item.value}
            className={`${s.item} ${selected === item.value ? s.selected : ''}`}
          >
            <input
              type="radio"
              name={`likert-${question.id}`}
              value={item.value}
              checked={selected === item.value}
              onChange={() => onChange(item.value)}
              className={s.radio}
            />
            <span className={s.dot} />
            <span className={s.label}>{item.label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
