import { useMemo } from 'react';
import type { Question } from '@/types';
import s from './CategorizeQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function CategorizeQuestion({ question, value, onChange }: Props) {
  const mapping = (value as Record<string, string[]> | undefined) ?? {};
  const options = question.options ?? [];

  const categories = useMemo(() => {
    const cats = new Set<string>();
    options.forEach((opt) => {
      if (opt.category_key) cats.add(opt.category_key);
    });
    return Array.from(cats);
  }, [options]);

  const assignedIds = useMemo(() => {
    const ids = new Set<string>();
    Object.values(mapping).forEach((arr) => arr.forEach((id) => ids.add(id)));
    return ids;
  }, [mapping]);

  const unassigned = options.filter((opt) => !assignedIds.has(opt.id));

  const assignToCategory = (optionId: string, category: string) => {
    const next = { ...mapping };
    // Remove from all categories first
    for (const cat of Object.keys(next)) {
      next[cat] = next[cat].filter((id) => id !== optionId);
      if (next[cat].length === 0) delete next[cat];
    }
    // Add to target category
    if (category) {
      next[category] = [...(next[category] ?? []), optionId];
    }
    onChange(next);
  };

  const removeFromCategory = (optionId: string, category: string) => {
    const next = { ...mapping };
    next[category] = (next[category] ?? []).filter((id) => id !== optionId);
    if (next[category].length === 0) delete next[category];
    onChange(next);
  };

  const optionMap = new Map(options.map((o) => [o.id, o]));

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />

      {unassigned.length > 0 && (
        <div className={s.pool}>
          <div className={s.poolLabel}>Unassigned items</div>
          <div className={s.poolItems}>
            {unassigned.map((opt) => (
              <div key={opt.id} className={s.chip}>
                <span dangerouslySetInnerHTML={{ __html: opt.content }} />
                <select
                  className={s.chipSelect}
                  value=""
                  onChange={(e) => assignToCategory(opt.id, e.target.value)}
                >
                  <option value="">Assign to…</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={s.categories}>
        {categories.map((cat) => {
          const ids = mapping[cat] ?? [];
          return (
            <div key={cat} className={s.category}>
              <div className={s.catHeader}>{cat}</div>
              <div className={s.catBody}>
                {ids.length === 0 && (
                  <span className={s.empty}>No items assigned</span>
                )}
                {ids.map((id) => {
                  const opt = optionMap.get(id);
                  if (!opt) return null;
                  return (
                    <div key={id} className={s.catChip}>
                      <span dangerouslySetInnerHTML={{ __html: opt.content }} />
                      <button
                        type="button"
                        className={s.removeBtn}
                        onClick={() => removeFromCategory(id, cat)}
                        aria-label="Remove"
                      >
                        ×
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
