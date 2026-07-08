import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { renderWithQueryClient } from './test-utils';
import { handlers } from '../mocks/handlers';
import App from '../App';
import { MOCK_TASK_ID } from '../mocks/fixtures';

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('User Flows', () => {
  it('Config page renders and allows form input', async () => {
    renderWithQueryClient(<App />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/base url/i), 'https://rag.test.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test');

    await user.click(screen.getByRole('button', { name: /save/i }));
    // After saving config, the start button should appear
    expect(screen.getByRole('button', { name: /start evaluation/i })).toBeInTheDocument();
  });

  it('Results page shows metric scores', async () => {
    window.history.pushState({}, '', `/task/${MOCK_TASK_ID}/results`);
    renderWithQueryClient(<App />);

    await waitFor(() => {
      expect(screen.getByText('FaithfulnessMetric')).toBeInTheDocument();
    });
    expect(screen.getByText('92.0%')).toBeInTheDocument();
  });

  it('History sidebar shows past tasks', async () => {
    renderWithQueryClient(<App />);

    await waitFor(() => {
      expect(screen.getByText(/COMPLETED/)).toBeInTheDocument();
    });
  });
});
