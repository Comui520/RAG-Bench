import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { GoldenCard } from '../components/GoldenCard';

describe('GoldenCard', () => {
  it('renders input and expected output', () => {
    renderWithProviders(
      <GoldenCard index={0} input="What is X?" expectedOutput="X is a thing." />
    );
    expect(screen.getByText(/What is X?/)).toBeInTheDocument();
    expect(screen.getByText('X is a thing.')).toBeInTheDocument();
  });

  it('shows context when provided', () => {
    renderWithProviders(
      <GoldenCard index={0} input="Q" expectedOutput="A" context='["chunk 1", "chunk 2"]' />
    );
    expect(screen.getByText('chunk 1')).toBeInTheDocument();
  });
});
