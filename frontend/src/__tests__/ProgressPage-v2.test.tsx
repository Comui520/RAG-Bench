import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { ProgressPage } from '../pages/ProgressPage';

describe('ProgressPage v2', () => {
  it('shows connecting state initially', () => {
    renderWithProviders(<ProgressPage />);
    expect(screen.getByText(/正在连接评估进度/i)).toBeInTheDocument();
  });
});
