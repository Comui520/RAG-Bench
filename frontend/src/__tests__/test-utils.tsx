import type { ReactElement } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

/** Renders a component wrapped with a test QueryClient and MemoryRouter. */
export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
    options
  );
}

/** Renders a component wrapped only with a test QueryClient (no router).
 *  Use for components that already provide their own router (e.g. <App />). */
export function renderWithQueryClient(ui: ReactElement, options?: RenderOptions) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
    options
  );
}

export { render as bareRender } from '@testing-library/react';
