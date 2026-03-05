import type { Question } from '@/types';
import s from './ImageMCQQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function ImageMCQQuestion({ question, value, onChange }: Props) {
  const selected = value as string | undefined;
  const options = question.options ?? [];

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      {question.image_url && (
        <img src={question.image_url} alt="Question" className={s.questionImage} />
      )}
      <div className={s.grid}>
        {options.map((opt) => (
          <button
            key={opt.id}
            type="button"
            className={`${s.card} ${selected === opt.id ? s.selected : ''}`}
            onClick={() => onChange(opt.id)}
          >
            {opt.image_url && (
              <img src={opt.image_url} alt={opt.content} className={s.optionImage} />
            )}
            <span className={s.label} dangerouslySetInnerHTML={{ __html: opt.content }} />
          </button>
        ))}
      </div>
    </div>
  );
}
