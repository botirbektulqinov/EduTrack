import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Toaster } from 'react-hot-toast';

import { useAuthStore } from '@/app/store';
import { renderWithProviders } from '@/test/render';
import LoginPage from './LoginPage';
import api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  });

  it('shows client-side validation for a missing password', async () => {
    renderWithProviders(
      <>
        <LoginPage />
        <Toaster />
      </>,
      { route: '/login' },
    );

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'student@example.edu' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText('Password is required')).toBeInTheDocument();
    expect(mockedApi.post).not.toHaveBeenCalled();
  });

  it('displays the API login error to the user', async () => {
    mockedApi.post.mockRejectedValueOnce({
      response: { data: { message: 'Invalid email or password' } },
    });

    renderWithProviders(
      <>
        <LoginPage />
        <Toaster />
      </>,
      { route: '/login' },
    );

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'student@example.edu' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrong-password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid email or password')).toBeInTheDocument();
    });
  });
});
