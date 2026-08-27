import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { ModelSelector } from '../components/ModelSelector';

describe('ModelSelector', () => {
  const defaultConfig = {
    provider: 'deepseek', api_format: 'openai_chat', model_name: 'deepseek-chat',
    api_key: '', base_url: 'https://api.deepseek.com',
  };

  it('renders provider selector and model', () => {
    renderWithProviders(<ModelSelector label="Test Model" value={defaultConfig} onChange={vi.fn()} />);
    expect(screen.getByText('Test Model')).toBeInTheDocument();
    expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument();
  });

  it('auto-fills base_url when provider changes', async () => {
    const onChange = vi.fn();
    renderWithProviders(<ModelSelector label="Test" value={{ ...defaultConfig, provider: 'custom', base_url: '' }} onChange={onChange} />);
    await userEvent.selectOptions(screen.getAllByRole('combobox')[0], 'openai');
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ provider: 'openai', base_url: 'https://api.openai.com/v1', api_format: 'openai_json' }));
  });

  it('has password visibility toggle', async () => {
    renderWithProviders(<ModelSelector label="Test" value={defaultConfig} onChange={vi.fn()} />);
    const input = screen.getByPlaceholderText('sk-...');
    expect(input).toHaveAttribute('type', 'password');
  });
});
