import { MapContainer, TileLayer, CircleMarker, Tooltip as LeafletTooltip } from 'react-leaflet';

export interface IncidentMapMarker {
  lat: number;
  lon: number;
  weight?: number;
  severity?: string;
  type?: string;
}

interface IncidentMapProps {
  center: [number, number];
  zoom?: number;
  markers: IncidentMapMarker[];
  variant?: 'single' | 'heat';
  heightClassName?: string;
  className?: string;
  showTooltip?: boolean;
  showAttribution?: boolean;
}

const MAP_TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const MAP_ATTRIBUTION = '&copy; OpenStreetMap contributors &copy; CARTO';

const IncidentMap = ({
  center,
  zoom = 12,
  markers,
  variant = 'heat',
  heightClassName = 'h-[360px]',
  className = '',
  showTooltip = true,
  showAttribution = true
}: IncidentMapProps) => {
  return (
    <div className={`${heightClassName} rounded-2xl overflow-hidden border border-white/10 ${className}`}>
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={false}
        attributionControl={showAttribution}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer attribution={MAP_ATTRIBUTION} url={MAP_TILE_URL} />
        {markers.map((point, idx) => {
          const radius = variant === 'single'
            ? 9
            : 5 + Math.max(point.weight || 1, 1) * 2.5;
          const color = variant === 'single' ? '#ef4444' : '#f97316';
          const fillOpacity = variant === 'single' ? 0.55 : 0.3;

          return (
            <CircleMarker
              key={`${point.lat}-${point.lon}-${idx}`}
              center={[point.lat, point.lon]}
              radius={radius}
              pathOptions={{ color, fillColor: color, fillOpacity, weight: 1 }}
            >
              {showTooltip && (
                <LeafletTooltip>
                  <div className="text-xs">
                    <div>Type: {point.type || 'N/A'}</div>
                    <div>Severity: {point.severity || 'N/A'}</div>
                  </div>
                </LeafletTooltip>
              )}
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
};

export default IncidentMap;
