import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { FileUploader } from '../components/FileUploader';

describe('FileUploader v2', () => {
  it('shows remove button on uploaded files when onRemove provided', () => {
    renderWithProviders(
      <FileUploader
        onUpload={vi.fn()}
        onRemove={vi.fn()}
        files={[{ id: 1, filename: 'doc.txt', file_size: 1024 }]}
      />
    );
    expect(screen.getByText('doc.txt')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument();
  });

  it('does not show remove button without onRemove', () => {
    renderWithProviders(
      <FileUploader onUpload={vi.fn()} files={[{ id: 1, filename: 'doc.txt', file_size: 1024 }]} />
    );
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument();
  });
});
