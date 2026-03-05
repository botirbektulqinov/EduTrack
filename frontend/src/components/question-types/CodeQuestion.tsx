import type { Question } from '@/types';
import s from './CodeQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function CodeQuestion({ question, value, onChange }: Props) {
  const code = (value as string) ?? '';

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.currentTarget;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const newValue = code.substring(0, start) + '  ' + code.substring(end);
      onChange(newValue);
      requestAnimationFrame(() => {
        target.selectionStart = target.selectionEnd = start + 2;
      });
    }
  };

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <div className={s.editorWrap}>
        <div className={s.lineNumbers}>
          {(code || ' ').split('\n').map((_, i) => (
            <span key={i}>{i + 1}</span>
          ))}
        </div>
        <textarea
          className={s.editor}
          value={code}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="// Write your code here…"
          spellCheck={false}
          rows={12}
        />
      </div>
    </div>
  );
}
