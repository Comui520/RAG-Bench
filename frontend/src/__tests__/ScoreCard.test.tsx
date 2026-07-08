import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { ScoreCard } from '../components/ScoreCard';

describe('ScoreCard', () => {
  it('renders metric name and score', () => {
    renderWithProviders(<ScoreCard name="Faithfulness" score={0.92} />);
    expect(screen.getByText('Faithfulness')).toBeInTheDocument();
    expect(screen.getByText('92.0%')).toBeInTheDocument();
  });
});
