import type { Pack } from '../types';
import { PACK_COLORS, PACK_LABELS } from '../types';

interface Props {
  packs: Pack[];
  activePack: string;
  onChange: (packId: string) => void;
}

export default function PackSelector({ packs, activePack, onChange }: Props) {
  return (
    <div className="flex items-center gap-1.5">
      {packs.map(p => (
        <button
          key={p.id}
          onClick={() => onChange(p.id)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
            activePack === p.id
              ? `${PACK_COLORS[p.id] ?? 'bg-gray-600'} text-white shadow-sm`
              : 'bg-surface-overlay text-text-muted hover:text-text'
          }`}
          title={p.name}
        >
          {PACK_LABELS[p.id] ?? p.id}
        </button>
      ))}
    </div>
  );
}
