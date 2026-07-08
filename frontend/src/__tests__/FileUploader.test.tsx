import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { FileUploader } from '../components/FileUploader';

describe('FileUploader', () => {
  it('renders drop zone', () => {
    renderWithProviders(<FileUploader onUpload={vi.fn()} />);
    expect(screen.getByText(/drag.*file/i)).toBeInTheDocument();
  });

  it('shows uploaded file names', () => {
    renderWithProviders(
      <FileUploader
        onUpload={vi.fn()}
        files={[{ id: 1, filename: 'doc.txt', file_size: 1024 }]}
      />
    );
    expect(screen.getByText('doc.txt')).toBeInTheDocument();
  });
});
