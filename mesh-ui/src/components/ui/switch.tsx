//components/ui/switch.tsx// src/components/ui/switch.tsx
import { cn } from '@/lib/utils';

type Props = {
  checked?: boolean;
  onCheckedChange?: (value: boolean) => void;
};

export function Switch({ checked, onCheckedChange }: Props) {
  return (
    <button
      type="button"
      onClick={() => onCheckedChange?.(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full border transition-colors',
        checked
          ? 'bg-violet-600 border-violet-600'
          : 'bg-slate-200 border-slate-300',
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
          checked ? 'translate-x-5' : 'translate-x-1',
        )}
      />
    </button>
  );
}
