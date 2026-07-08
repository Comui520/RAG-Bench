import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { ProgressTracker } from '../components/ProgressTracker';

describe('ProgressTracker', () => {
  it('shows all phases', () => {
    renderWithProviders(
      <ProgressTracker phase="GENERATING_GOLDENS" progress={0.3} status="GENERATING_GOLDENS" />
    );
    expect(screen.getByText('Generating Goldens')).toBeInTheDocument();
    expect(screen.getByText('Running Evaluation')).toBeInTheDocument();
  });

  it('shows progress percentage', () => {
    renderWithProviders(
      <ProgressTracker phase="RUNNING_EVAL" progress={0.75} status="RUNNING_EVAL" />
    );
    expect(screen.getByText('75%')).toBeInTheDocument();
  });
});
