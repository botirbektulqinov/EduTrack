/* ─── EduTrack — Application Entry Point ─── */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { router } from '@/app/router';
import { queryClient } from '@/app/queryClient';
import '@/styles/global.scss';

/* Apply persisted theme before first paint to prevent flash */
(() => {
  try {
    const stored = localStorage.getItem('edutrack-ui');
    if (stored) {
      const theme = JSON.parse(stored).state?.theme;
      if (theme) document.documentElement.setAttribute('data-theme', theme);
    }
  } catch { /* ignore */ }
})();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.875rem',
          },
        }}
      />
    </QueryClientProvider>
  </StrictMode>,
);
