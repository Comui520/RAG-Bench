import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { ConfirmButton } from '../components/ConfirmButton';

describe('ConfirmButton', () => {
  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    renderWithProviders(
      <ConfirmButton onClick={onClick} loading={false} disabled={false} goldensCount={5} />
    );
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled when goldensCount is 0', () => {
    renderWithProviders(
      <ConfirmButton onClick={vi.fn()} loading={false} disabled={false} goldensCount={0} />
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('shows loading state', () => {
    renderWithProviders(
      <ConfirmButton onClick={vi.fn()} loading={true} disabled={false} goldensCount={3} />
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
