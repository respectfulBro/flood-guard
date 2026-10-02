import React from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import { TIER_HEX } from "@/lib/riskTiers";
import RiskBadge from "@/components/risk/RiskBadge";

const CONFIDENCE_RADIUS = { low: 7, medium: 10, high: 13 };

function MapResizer() {
  const map = useMap();
  React.useEffect(() => {
    const id = setTimeout(() => map.invalidateSize(), 50);
    return () => clearTimeout(id);
  }, [map]);
  return null;
}

export default function RiskMapView({ areas, showConfidence = false }) {
  const navigate = useNavigate();
  return (
    <div className="rounded-2xl overflow-hidden border border-slate-100 h-[520px] w-full">
      <MapContainer
        center={[6.52, 3.43]}
        zoom={11}
        scrollWheelZoom
        style={{ height: "100%", width: "100%" }}
      >
        <MapResizer />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {areas.map((area) => (
          <CircleMarker
            key={area.id}
            center={[area.lat, area.lng]}
            radius={showConfidence ? (CONFIDENCE_RADIUS[area.confidence] || 9) : 9}
            pathOptions={{
              color: TIER_HEX[area.risk_tier] || TIER_HEX.unavailable,
              fillColor: TIER_HEX[area.risk_tier] || TIER_HEX.unavailable,
              fillOpacity: showConfidence ? 0.35 + (area.confidence === "high" ? 0.35 : area.confidence === "medium" ? 0.2 : 0.05) : 0.6,
              weight: 2,
            }}
            eventHandlers={{ click: () => navigate(`/area/${area.id}`) }}
          >
            <Popup>
              <div className="space-y-1.5">
                <p className="font-semibold text-slate-900">{area.name}</p>
                <p className="text-xs text-slate-500">{area.country}</p>
                <div>{area.data_status === "historical" && <p className="text-xs text-amber-900 mb-1">Historical · {area.event_date}</p>}<RiskBadge tier={area.risk_tier} /></div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}