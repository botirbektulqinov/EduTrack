import { useMemo } from 'react';
import type { Question } from '@/types';
import s from './MatchingQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function MatchingQuestion({ question, value, onChange }: Props) {
  const mapping = (value as Record<string, string> | undefined) ?? {};
  const options = question.options ?? [];

  const matchKeys = useMemo(() => {
    const keys = new Set<string>();
    options.forEach((opt) => {
      if (opt.match_key) keys.add(opt.match_key);
    });
    return Array.from(keys);
  }, [options]);

  const handleSelect = (optionId: string, matchKey: string) => {
    const next = { ...mapping, [optionId]: matchKey };
    if (!matchKey) delete next[optionId];
    onChange(next);
  };

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <div className={s.table}>
        <div className={`${s.row} ${s.header}`}>
          <div className={s.cell}>Item</div>
          <div className={s.cell}>Match</div>
        </div>
        {options.map((opt) => (
          <div key={opt.id} className={s.row}>
            <div className={s.cell}>
              <span dangerouslySetInnerHTML={{ __html: opt.content }} />
            </div>
            <div className={s.cell}>
              <select
                className={s.select}
                value={mapping[opt.id] ?? ''}
                onChange={(e) => handleSelect(opt.id, e.target.value)}
              >
                <option value="">— Select —</option>
                {matchKeys.map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
