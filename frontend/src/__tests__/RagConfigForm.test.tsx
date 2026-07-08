import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { RagConfigForm } from '../components/RagConfigForm';

describe('RagConfigForm', () => {
  it('renders url and api key inputs', () => {
    renderWithProviders(<RagConfigForm onSubmit={vi.fn()} />);
    expect(screen.getByLabelText(/base url/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api key/i)).toBeInTheDocument();
  });

  it('calls onSubmit with form data when valid', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/base url/i), 'https://rag.test.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-123');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(onSubmit).toHaveBeenCalledWith({
      rag_base_url: 'https://rag.test.com/v1',
      rag_api_key: 'sk-test-123',
    });
  });

  it('shows validation error when fields are empty', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RagConfigForm onSubmit={onSubmit} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /save/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
