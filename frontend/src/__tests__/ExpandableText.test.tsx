import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import { ExpandableText } from '../components/ExpandableText';
import { DetailTable } from '../components/DetailTable';

const longText = '这是一段很长的测试文本，用于验证界面不会直接隐藏内容，而是提供展开按钮让用户查看完整信息。'.repeat(3);

describe('ExpandableText', () => {
  it('shows an expand control for long text and reveals the full value', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ExpandableText text={longText} threshold={10} />);

    expect(screen.getByRole('button', { name: '展开' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '展开' }));
    expect(screen.getByRole('button', { name: '收起' })).toBeInTheDocument();
    expect(screen.getByText(longText)).toBeInTheDocument();
  });
});

describe('DetailTable', () => {
  it('provides independent expand controls for question and expected answer', () => {
    renderWithProviders(
      <DetailTable
        details={[{
          id: 1,
          golden_id: 1,
          input: longText,
          expected_output: longText,
          actual_output: 'actual',
          retrieval_context: null,
          metrics: [],
          passed: true,
        }]}
      />
    );

    expect(screen.getAllByRole('button', { name: '展开' })).toHaveLength(2);
  });
});
