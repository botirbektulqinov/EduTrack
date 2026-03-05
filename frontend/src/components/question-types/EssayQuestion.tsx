import type { Question } from '@/types';
import s from './EssayQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function EssayQuestion({ question, value, onChange }: Props) {
  const text = (value as string) ?? '';

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <textarea
        className={s.textarea}
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Write your essay here…"
        rows={10}
      />
      <div className={s.counter}>{text.length} characters</div>
    </div>
  );
}
