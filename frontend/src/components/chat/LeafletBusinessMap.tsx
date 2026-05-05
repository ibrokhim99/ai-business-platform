'use client';

import { useEffect, useMemo } from 'react';
import L from 'leaflet';
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import type { BusinessMapMarker } from '@/lib/chat/types';
import { fmtMoney, fmtPct } from '@/lib/chat/format';

interface Props {
  center: { lat: number; lon: number };
  radius_m: number;
  markers: BusinessMapMarker[];
}

const OUTCOME_COLORS: Record<BusinessMapMarker['outcome'], string> = {
  succeeded: '#10b981',
  struggling: '#f59e0b',
  failed: '#ef4444',
};

function markerIcon(outcome: BusinessMapMarker['outcome']) {
  return L.divIcon({
    className: 'business-map-marker-wrap',
    html: `<span class="business-map-marker business-map-marker-${outcome}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -8],
  });
}

function FitBounds({ center, markers }: { center: Props['center']; markers: BusinessMapMarker[] }) {
  const map = useMap();

  useEffect(() => {
    const points: [number, number][] = [[center.lat, center.lon]];
    for (const marker of markers) points.push([marker.lat, marker.lon]);

    if (points.length === 1) {
      map.setView(points[0], 13);
      return;
    }

    map.fitBounds(points, { padding: [28, 28], maxZoom: 15 });
  }, [center.lat, center.lon, map, markers]);

  return null;
}

export function LeafletBusinessMap({ center, radius_m, markers }: Props) {
  const icons = useMemo(
    () => ({
      succeeded: markerIcon('succeeded'),
      struggling: markerIcon('struggling'),
      failed: markerIcon('failed'),
    }),
    [],
  );

  return (
    <MapContainer
      center={[center.lat, center.lon]}
      zoom={13}
      scrollWheelZoom={false}
      className="h-full w-full"
      attributionControl
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Circle
        center={[center.lat, center.lon]}
        radius={radius_m}
        pathOptions={{
          color: '#6366f1',
          fillColor: '#6366f1',
          fillOpacity: 0.08,
          opacity: 0.5,
          weight: 1,
        }}
      />
      {markers.map((marker) => (
        <Marker
          key={marker.id}
          position={[marker.lat, marker.lon]}
          icon={icons[marker.outcome]}
        >
          <Popup>
            <div className="min-w-[190px] text-[12px]">
              <div className="font-semibold text-zinc-900">{marker.niche_label}</div>
              <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-zinc-600">
                <span>Daromad</span>
                <span className="text-right text-zinc-900">{fmtMoney(marker.monthly_revenue)}</span>
                <span>Sof oqim</span>
                <span className={marker.monthly_net_cash_flow >= 0 ? 'text-right text-emerald-600' : 'text-right text-rose-600'}>
                  {fmtMoney(marker.monthly_net_cash_flow)}
                </span>
                <span>O'sish</span>
                <span className={marker.growth_rate_pct >= 0 ? 'text-right text-emerald-600' : 'text-right text-rose-600'}>
                  {fmtPct(marker.growth_rate_pct, 1)}
                </span>
                <span>Raqobatchi</span>
                <span className="text-right text-zinc-900">{marker.competitor_count}</span>
              </div>
              <div
                className="mt-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium text-white"
                style={{ backgroundColor: OUTCOME_COLORS[marker.outcome] }}
              >
                {marker.outcome === 'succeeded' ? 'Muvaffaqiyatli' : marker.outcome === 'struggling' ? 'Qiyin holatda' : 'Muvaffaqiyatsiz'}
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
      <FitBounds center={center} markers={markers} />
    </MapContainer>
  );
}
