import { useState, type FormEvent } from 'react';

interface RagConfig {
  rag_base_url: string;
  rag_api_key: string;
}

interface Props {
  onSubmit: (config: RagConfig) => void;
}

export function RagConfigForm({ onSubmit }: Props) {
  const [url, setUrl] = useState('');
  const [key, setKey] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!url.trim()) errs.url = 'Base URL is required';
    if (!key.trim()) errs.key = 'API key is required';
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setErrors({});
    onSubmit({ rag_base_url: url.trim(), rag_api_key: key.trim() });
  }

  return (
    <div className="border rounded-lg bg-white p-6 space-y-4">
      <h3 className="text-lg font-semibold">RAG Service Configuration</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="base-url" className="block text-sm font-medium mb-1">Base URL</label>
          <input
            id="base-url"
            className="w-full border rounded-md px-3 py-2 text-sm"
            placeholder="https://your-rag-service.com/v1"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          {errors.url && <p className="text-red-500 text-sm mt-1">{errors.url}</p>}
        </div>
        <div>
          <label htmlFor="api-key" className="block text-sm font-medium mb-1">API Key</label>
          <input
            id="api-key"
            type="password"
            className="w-full border rounded-md px-3 py-2 text-sm"
            placeholder="sk-..."
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          {errors.key && <p className="text-red-500 text-sm mt-1">{errors.key}</p>}
        </div>
        <button type="submit" className="bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800">
          Save Configuration
        </button>
      </form>
    </div>
  );
}
