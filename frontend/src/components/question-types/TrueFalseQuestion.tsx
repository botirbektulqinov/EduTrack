import type { Question } from '@/types';
import s from './TrueFalseQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function TrueFalseQuestion({ question, value, onChange }: Props) {
  const current = value as string | undefined;
  const isYesNo = question.question_type === 'yes_no';
  const labelA = isYesNo ? 'Yes' : 'True';
  const labelB = isYesNo ? 'No' : 'False';
  const valA = isYesNo ? 'yes' : 'true';
  const valB = isYesNo ? 'no' : 'false';

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <div className={s.buttons}>
        <button
          type="button"
          className={`${s.btn} ${current === valA ? s.selected : ''}`}
          onClick={() => onChange(valA)}
        >
          {labelA}
        </button>
        <button
          type="button"
          className={`${s.btn} ${current === valB ? s.selected : ''}`}
          onClick={() => onChange(valB)}
        >
          {labelB}
        </button>
      </div>
    </div>
  );
}
