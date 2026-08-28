import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  text: string | null | undefined;
  threshold?: number;
  lines?: number;
  className?: string;
}

/** Displays long text safely without hiding the full value behind an ellipsis. */
export function ExpandableText({ text, threshold = 100, lines = 2, className = '' }: Props) {
  const value = text ?? '';
  const [expanded, setExpanded] = useState(false);
  const canExpand = value.length > threshold || value.includes('\n');

  return (
    <div className={`min-w-0 ${className}`}>
      <p
        className={`break-words whitespace-pre-wrap text-sm ${
          canExpand && !expanded ? 'overflow-hidden' : ''
        }`}
        style={canExpand && !expanded ? {
          display: '-webkit-box',
          WebkitBoxOrient: 'vertical',
          WebkitLineClamp: lines,
        } : undefined}
      >
        {value || '—'}
      </p>
      {canExpand && (
        <button
          type="button"
          className="mt-1 inline-flex items-center gap-0.5 text-xs font-medium text-indigo-600 hover:text-indigo-800"
          onClick={(event) => {
            event.stopPropagation();
            setExpanded((current) => !current);
          }}
          aria-expanded={expanded}
        >
          {expanded ? '收起' : '展开'}
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
      )}
    </div>
  );
}
