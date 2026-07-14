import { Loader2, CheckCircle } from 'lucide-react';

interface Props {
  onClick: () => void;
  loading: boolean;
  disabled: boolean;
  goldensCount: number;
}

export function ConfirmButton({ onClick, loading, disabled, goldensCount }: Props) {
  return (
    <button
      className={`w-full py-3 rounded-md text-white font-medium flex items-center justify-center gap-2 active:scale-95 transition-transform ${
        disabled || loading || goldensCount === 0 ? 'bg-slate-300 cursor-not-allowed' : 'bg-slate-900 hover:bg-slate-800'
      }`}
      onClick={onClick}
      disabled={disabled || loading || goldensCount === 0}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {!loading && <CheckCircle className="w-4 h-4" />}
      Confirm {goldensCount} Goldens & Run Evaluation
    </button>
  );
}
