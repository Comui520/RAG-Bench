import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { RagConfigForm } from '../components/RagConfigForm';

describe('RagConfigForm v2', () => {
  it('renders three config sections', () => {
    renderWithProviders(<RagConfigForm onSubmit={vi.fn()} />);
    expect(screen.getByText(/被测服务/i)).toBeInTheDocument();
    expect(screen.getByText(/评测模型/i)).toBeInTheDocument();
    expect(screen.getByText(/嵌入模型/i)).toBeInTheDocument();
  });

  it('shows validation errors when fields are empty', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole('button', { name: /保存配置|已保存/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('calls onSubmit with full config when valid', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    const user = userEvent.setup();
    const inputs = screen.getAllByPlaceholderText(/https:\/\/your-rag/i);
    await user.type(inputs[0], 'https://rag.test.com');
    const keys = screen.getAllByPlaceholderText('sk-...');
    await user.type(keys[0], 'sk-rag');
    await user.type(keys[1], 'sk-eval');
    await user.type(keys[2], 'sk-embed');
    await user.click(screen.getByRole('button', { name: /保存配置|已保存/i }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      rag_base_url: 'https://rag.test.com',
      rag_api_key: 'sk-rag',
      eval_model: expect.objectContaining({ api_key: 'sk-eval' }),
      embed_model: expect.objectContaining({ api_key: 'sk-embed' }),
    }));
  });
});
