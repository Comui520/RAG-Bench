import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { renderWithProviders } from './test-utils';
import { handlers } from '../mocks/handlers';
import { HistoryPage } from '../pages/HistoryPage';

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('HistoryPage', () => {
  it('paginates history cards and keeps actions visible per card', async () => {
    const records = Array.from({ length: 17 }, (_, index) => ({
      task_id: `task-${String(index + 1).padStart(2, '0')}`,
      task_name: `回归测试 ${index + 1}`,
      status: 'COMPLETED',
      rag_base_url: 'http://localhost:8001',
      created_at: '2026-08-28T03:50:00Z',
      completed_at: '2026-08-28T03:51:00Z',
    }));
    server.use(http.get('http://localhost:8000/api/history', () => HttpResponse.json(records)));

    renderWithProviders(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getAllByRole('article')).toHaveLength(8);
    });
    expect(screen.getByRole('navigation', { name: '历史记录分页' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '查看结果' })).toHaveLength(8);
    expect(screen.getAllByRole('button', { name: '删除记录' })).toHaveLength(8);

    await screen.getByRole('button', { name: '下一页' }).click();
    await waitFor(() => {
      expect(screen.getAllByRole('article')).toHaveLength(8);
    });
    expect(screen.getByText('回归测试 9')).toBeInTheDocument();
  });
});
