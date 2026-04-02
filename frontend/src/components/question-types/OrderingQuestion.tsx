import type { Question } from '@/types';
import s from './OrderingQuestion.module.scss';

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function OrderingQuestion({ question, value, onChange }: Props) {
  const options = question.options ?? [];
  const order = Array.isArray(value) && value.length > 0 ? (value as string[]) : options.map((option) => option.id);

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= order.length) return;
    const next = [...order];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  const optionMap = new Map(options.map((o) => [o.id, o]));

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <p className={s.hint}>Use the arrows to reorder the items</p>
      <div className={s.list}>
        {order.map((id, index) => {
          const opt = optionMap.get(id);
          if (!opt) return null;
          return (
            <div key={id} className={s.item}>
              <span className={s.index}>{index + 1}</span>
              <span className={s.label} dangerouslySetInnerHTML={{ __html: opt.content }} />
              <div className={s.arrows}>
                <button
                  type="button"
                  className={s.arrowBtn}
                  disabled={index === 0}
                  onClick={() => move(index, -1)}
                  aria-label="Move up"
                >
                  ▲
                </button>
                <button
                  type="button"
                  className={s.arrowBtn}
                  disabled={index === order.length - 1}
                  onClick={() => move(index, 1)}
                  aria-label="Move down"
                >
                  ▼
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
