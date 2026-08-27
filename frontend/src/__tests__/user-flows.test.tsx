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

    // Fill RAG config using placeholder selectors
    const ragUrlInput = screen.getByPlaceholderText('https://your-rag-service.com/v1');
    await user.type(ragUrlInput, 'https://rag.test.com/v1');
    const keyInputs = screen.getAllByPlaceholderText('sk-...');
    await user.type(keyInputs[0], 'sk-test');
    await user.type(keyInputs[1], 'sk-eval');
    await user.type(keyInputs[2], 'sk-embed');

    await user.click(screen.getByRole('button', { name: /保存配置|已保存/i }));
    // After saving config, the start button should appear
    expect(screen.getByRole('button', { name: /开始评估/i })).toBeInTheDocument();
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
      expect(screen.getByText(/已完成/)).toBeInTheDocument();
    });
  });
});
