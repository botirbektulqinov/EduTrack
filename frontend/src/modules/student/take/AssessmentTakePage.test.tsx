import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/render';
import AssessmentTakePage from './AssessmentTakePage';
import api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/hooks/useProctoring', () => ({
  useProctoring: () => ({
    enterFullscreen: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    send: vi.fn(),
    connected: true,
  }),
}));

vi.mock('@/hooks/useAutoSave', () => ({
  useAutoSave: () => undefined,
}));

const mockedApi = vi.mocked(api);

describe('AssessmentTakePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.get.mockResolvedValue({
      data: {
        data: {
          assessment: {
            id: 'assessment-1',
            title: 'Algebra Quiz',
            description: 'Short practice quiz',
            assessment_type: 'quiz',
            time_limit_minutes: 10,
            max_attempts: 1,
            passing_score: 70,
            max_violations: 3,
            time_penalty_minutes: 2,
            enforce_fullscreen: false,
            block_keyboard_shortcuts: true,
            tab_switch_detection: true,
            devtools_detection: true,
            right_click_block: true,
            copy_paste_block: true,
          },
        },
      },
    });
    mockedApi.post.mockImplementation((url: string) => {
      if (url.endsWith('/start')) {
        return Promise.resolve({
          data: {
            data: {
              attempt_id: 'attempt-1',
              server_token: 'server-token',
              time_limit_seconds: 600,
              questions: [
                {
                  id: 'question-1',
                  assessment_id: 'assessment-1',
                  question_type: 'mcq_single',
                  content: 'Pick the correct answer',
                  points: 1,
                  partial_scoring: false,
                  negative_marking: 0,
                  options: [
                    {
                      id: 'option-1',
                      question_id: 'question-1',
                      content: 'Correct',
                      is_correct: true,
                    },
                  ],
                },
              ],
            },
          },
        });
      }

      return Promise.resolve({ data: { data: {} } });
    });
  });

  it('opens a submit confirmation before submitting an active attempt', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/take/:token" element={<AssessmentTakePage />} />
      </Routes>,
      { route: '/take/public-token' },
    );

    expect(await screen.findByRole('heading', { name: 'Algebra Quiz' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /begin assessment/i }));

    expect(await screen.findByText('Pick the correct answer')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^submit$/i }));

    expect(await screen.findByRole('heading', { name: 'Submit Assessment' })).toBeInTheDocument();
    expect(screen.getByText('You have 1 unanswered question(s). Submit anyway?')).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /^submit$/i }));

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith('/student/attempts/attempt-1/submit');
    });
  });
});
