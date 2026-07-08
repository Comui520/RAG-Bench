import { useCallback, useState } from 'react';
import { Upload, FileText } from 'lucide-react';
import type { UploadedFile } from '../types';

interface Props {
  onUpload: (files: File[]) => Promise<void>;
  files?: UploadedFile[];
  disabled?: boolean;
}

export function FileUploader({ onUpload, files = [], disabled }: Props) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const dropped = Array.from(e.dataTransfer.files);
      onUpload(dropped);
    },
    [onUpload, disabled]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onUpload(Array.from(e.target.files));
    }
  };

  return (
    <div className="border rounded-lg bg-white p-6">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto w-8 h-8 text-slate-400 mb-2" />
        <p className="text-sm text-slate-600">
          Drag & drop knowledge base files here, or{' '}
          <label className="text-blue-600 hover:underline cursor-pointer">
            browse
            <input
              type="file"
              multiple
              accept=".txt,.md,.pdf,.json,.csv,.rst,.html"
              className="hidden"
              onChange={handleChange}
              disabled={disabled}
            />
          </label>
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Supported: .txt, .md, .pdf, .json, .csv
        </p>
      </div>

      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((f) => (
            <div key={f.id} className="flex items-center gap-2 text-sm text-slate-700">
              <FileText className="w-4 h-4 text-slate-400" />
              <span className="flex-1 truncate">{f.filename}</span>
              <span className="text-xs text-slate-400">{(f.file_size / 1024).toFixed(1)} KB</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
