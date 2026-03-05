import type { Question } from '@/types';
import s from './ShortAnswerQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function ShortAnswerQuestion({ question, value, onChange }: Props) {
  const text = (value as string) ?? '';

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <input
        type="text"
        className={s.input}
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Type your answer…"
        autoComplete="off"
      />
    </div>
  );
}
