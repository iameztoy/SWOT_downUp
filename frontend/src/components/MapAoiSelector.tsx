import { useMemo, useState } from 'react'
import { GeoJSON, MapContainer, TileLayer, useMapEvents } from 'react-leaflet'

function asFeature(geojson: GeoJSON.GeoJsonObject): GeoJSON.Feature {
  if (geojson.type === 'Feature') {
    return geojson
  }
  return {
    type: 'Feature',
    properties: {},
    geometry: geojson as GeoJSON.Geometry,
  }
}

type DrawMode = 'none' | 'rectangle' | 'polygon'

type Props = {
  geometry: GeoJSON.GeoJsonObject | null
  drawMode: DrawMode
  onGeometryChange: (geojson: GeoJSON.GeoJsonObject) => void
}

function DrawEvents({
  drawMode,
  points,
  setPoints,
  onGeometryChange,
}: {
  drawMode: DrawMode
  points: [number, number][]
  setPoints: (v: [number, number][]) => void
  onGeometryChange: (geojson: GeoJSON.GeoJsonObject) => void
}) {
  useMapEvents({
    click(event) {
      const lat = event.latlng.lat
      const lon = event.latlng.lng

      if (drawMode === 'rectangle') {
        const next = [...points, [lon, lat] as [number, number]]
        if (next.length < 2) {
          setPoints(next)
          return
        }

        const [a, b] = next
        const minx = Math.min(a[0], b[0])
        const maxx = Math.max(a[0], b[0])
        const miny = Math.min(a[1], b[1])
        const maxy = Math.max(a[1], b[1])
        onGeometryChange({
          type: 'Polygon',
          coordinates: [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]],
        })
        setPoints([])
      }

      if (drawMode === 'polygon') {
        setPoints([...points, [lon, lat]])
      }
    },
  })

  return null
}

export default function MapAoiSelector({ geometry, drawMode, onGeometryChange }: Props) {
  const [points, setPoints] = useState<[number, number][]>([])

  const pointPreview = useMemo(() => {
    if (drawMode !== 'polygon' || points.length < 3) {
      return null
    }
    return {
      type: 'Polygon',
      coordinates: [[...points, points[0]]],
    } as GeoJSON.Polygon
  }, [drawMode, points])

  return (
    <div className="map-shell">
      <MapContainer className="map-canvas" center={[20, 0]} zoom={2} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <DrawEvents drawMode={drawMode} points={points} setPoints={setPoints} onGeometryChange={onGeometryChange} />

        {geometry && <GeoJSON data={asFeature(geometry)} />}
        {pointPreview && <GeoJSON data={asFeature(pointPreview)} />}
      </MapContainer>

      <div className="map-controls">
        <p>Click map to draw AOI in selected draw mode.</p>
        {drawMode === 'polygon' && (
          <div className="inline-row">
            <span>Polygon points: {points.length}</span>
            <button
              type="button"
              onClick={() => {
                if (points.length < 3) return
                onGeometryChange({ type: 'Polygon', coordinates: [[...points, points[0]]] })
                setPoints([])
              }}
            >
              Finish Polygon
            </button>
            <button type="button" onClick={() => setPoints([])}>
              Clear Points
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
