import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Question } from '@/types';
import { QuestionRenderer } from './QuestionRenderer';

const baseQuestion: Question = {
  id: 'question-1',
  assessment_id: 'assessment-1',
  question_type: 'mcq_single',
  content: 'What is 2 + 2?',
  points: 1,
  partial_scoring: false,
  negative_marking: 0,
  options: [
    {
      id: 'option-1',
      question_id: 'question-1',
      content: '3',
      is_correct: false,
    },
    {
      id: 'option-2',
      question_id: 'question-1',
      content: '4',
      is_correct: true,
    },
  ],
};

describe('QuestionRenderer', () => {
  it('renders MCQ options and reports the selected option', () => {
    const onChange = vi.fn();

    render(<QuestionRenderer question={baseQuestion} value={undefined} onChange={onChange} />);

    expect(screen.getByText('What is 2 + 2?')).toBeInTheDocument();
    fireEvent.click(screen.getByText('4'));

    expect(onChange).toHaveBeenCalledWith('option-2');
  });

  it('shows a clear fallback for unsupported question types', () => {
    render(
      <QuestionRenderer
        question={{ ...baseQuestion, question_type: 'unknown_type' as Question['question_type'] }}
        value={undefined}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/Unsupported question type/i)).toBeInTheDocument();
  });
});
