'use client';

import dynamic from 'next/dynamic';
import { MapPin, Navigation, RadioTower } from 'lucide-react';
import type { Block, BusinessMapMarker } from '@/lib/chat/types';

const LeafletBusinessMap = dynamic(
  () => import('./LeafletBusinessMap').then((m) => m.LeafletBusinessMap),
  {
    ssr: false,
    loading: () => (
      <div className="h-full w-full grid place-items-center bg-panel text-xs text-muted">
        Xarita yuklanmoqda...
      </div>
    ),
  },
);

const OUTCOME_META: Record<BusinessMapMarker['outcome'], { label: string; cls: string }> = {
  succeeded: { label: 'Muvaffaqiyatli', cls: 'bg-emerald-500' },
  struggling: { label: 'Qiyin holatda', cls: 'bg-amber-500' },
  failed: { label: 'Muvaffaqiyatsiz', cls: 'bg-rose-500' },
};

function outcomeCounts(markers: BusinessMapMarker[]) {
  return markers.reduce(
    (acc, marker) => {
      acc[marker.outcome] += 1;
      return acc;
    },
    { succeeded: 0, struggling: 0, failed: 0 },
  );
}

export function BusinessMapBlock({ block }: { block: Extract<Block, { kind: 'business-map' }> }) {
  const counts = outcomeCounts(block.markers);

  if (!block.markers.length) return null;

  return (
    <div className="rounded-2xl border border-line bg-elev overflow-hidden fade-in">
      <div className="px-4 py-3 border-b border-line">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm font-medium text-fg">
              <MapPin className="w-4 h-4 text-accent" />
              <span className="truncate">{block.title}</span>
            </div>
            <div className="mt-1 text-xs text-muted">
              {block.profile.region_label} · {block.profile.mcc_label} · {block.markers.length} ta o'xshash biznes
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-line bg-panel px-2.5 py-1 text-[11px] text-muted">
            <Navigation className="w-3 h-3" />
            {Math.round(block.radius_m).toLocaleString()} m radius
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {(Object.keys(OUTCOME_META) as BusinessMapMarker['outcome'][]).map((outcome) => {
            const meta = OUTCOME_META[outcome];
            const count = counts[outcome];
            if (!count) return null;
            return (
              <span key={outcome} className="inline-flex items-center gap-1.5 text-[11px] text-muted">
                <span className={`w-2 h-2 rounded-full ${meta.cls}`} />
                {meta.label}: <span className="text-fg tabular-nums">{count}</span>
              </span>
            );
          })}
        </div>
      </div>

      <div className="relative h-[320px] md:h-[380px] bg-panel">
        <LeafletBusinessMap
          center={block.center}
          radius_m={block.radius_m}
          markers={block.markers}
        />
      </div>

      <div className="px-4 py-2 border-t border-line flex items-center gap-2 text-[11px] text-muted">
        <RadioTower className="w-3 h-3" />
        Markerlar sintetik datasetdagi o'xshash bizneslar asosida ko'rsatilgan.
      </div>
    </div>
  );
}
