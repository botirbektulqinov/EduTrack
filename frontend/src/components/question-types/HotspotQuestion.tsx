import { useRef, useCallback } from 'react';
import type { Question } from '@/types';
import s from './HotspotQuestion.module.scss';

interface HotspotValue {
  x: number;
  y: number;
}

interface Props {
  question: Question;
  value: unknown;
  onChange: (val: unknown) => void;
}

export function HotspotQuestion({ question, value, onChange }: Props) {
  const point = value as HotspotValue | undefined;
  const imgRef = useRef<HTMLImageElement>(null);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      onChange({ x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 });
    },
    [onChange],
  );

  return (
    <div className={s.wrapper}>
      <div className={s.content} dangerouslySetInnerHTML={{ __html: question.content }} />
      <p className={s.hint}>Click on the image to mark your answer</p>
      <div className={s.imageContainer} onClick={handleClick}>
        {question.image_url ? (
          <img
            ref={imgRef}
            src={question.image_url}
            alt="Hotspot"
            className={s.image}
            draggable={false}
          />
        ) : (
          <div className={s.placeholder}>No image provided</div>
        )}
        {point && (
          <div
            className={s.marker}
            style={{ left: `${point.x}%`, top: `${point.y}%` }}
          />
        )}
      </div>
    </div>
  );
}
