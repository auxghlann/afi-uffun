import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, CircleMarker, Tooltip as LeafletTooltip } from 'react-leaflet';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { Activity, ClipboardList, ShieldAlert, MapPinned } from 'lucide-react';
import { clearRole } from '../utils/auth';

interface MetricsResponse {
  total_reports: number;
  reports_24h: number;
  avg_severity_score: number;
  avg_severity_label: string;
  by_status: Record<string, number>;
  pending_reviews?: number;
}

interface BreakdownResponse {
  by_day: { date: string; count: number }[];
  by_type: { type: string; count: number }[];
}

interface HeatmapPoint {
  lat: number;
  lon: number;
  weight: number;
  severity?: string;
  type?: string;
}

interface ReportItem {
  id: number;
  call_id: string;
  status: string;
  emergency_types: string;
  severity: string;
  people_affected?: string;
  summary?: string;
  caller_lat?: number;
  caller_lon?: number;
  routed_hotlines?: { id?: number; type?: string; name?: string }[];
  timestamp?: string | null;
}

const pieColors = ['#ff4500', '#fb923c', '#facc15', '#22c55e', '#38bdf8'];
const center: [number, number] = [17.6134, 121.7269];

const AdminDashboard = () => {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [breakdown, setBreakdown] = useState<BreakdownResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapPoint[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [metricsRes, breakdownRes, heatmapRes, reportsRes] = await Promise.all([
        fetch('http://localhost:8000/api/admin/metrics'),
        fetch('http://localhost:8000/api/admin/breakdown'),
        fetch('http://localhost:8000/api/admin/heatmap'),
        fetch('http://localhost:8000/api/admin/reports?limit=12')
      ]);

      const metricsData = await metricsRes.json();
      const breakdownData = await breakdownRes.json();
      const heatmapData = await heatmapRes.json();
      const reportsData = await reportsRes.json();

      setMetrics(metricsData);
      setBreakdown(breakdownData);
      setHeatmap(heatmapData || []);
      setReports(reportsData || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const interval = window.setInterval(fetchAll, 10000);
    return () => window.clearInterval(interval);
  }, []);

  const statusStats = useMemo(() => {
    if (!metrics?.by_status) return [];
    return Object.entries(metrics.by_status).map(([status, count]) => ({
      status,
      count
    }));
  }, [metrics]);

  const avgSeverityLabel = metrics?.avg_severity_label || 'N/A';
  const avgSeverityScore = metrics?.avg_severity_score?.toFixed(2) || '0.00';

  const formatTime = (value?: string | null) => {
    if (!value) return 'N/A';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString();
  };

  return (
    <div className="min-h-screen bg-black text-white p-6 relative overflow-hidden">
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/10 blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[10%] right-[-10%] w-[45%] h-[45%] rounded-full bg-indigo-500/10 blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto space-y-8 relative z-10">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 glass rounded-2xl p-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-gradient mb-1">Admin Dashboard</h1>
            <p className="text-neutral-400 font-medium">Live metrics and dispatch analytics</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/admin/command-center"
              className="glass-panel hover:bg-white/10 px-5 py-2.5 rounded-xl font-medium transition-all"
            >
              Command Center
            </Link>
            <button
              onClick={() => {
                clearRole();
                window.location.href = '/login';
              }}
              className="glass-panel hover:bg-white/10 px-6 py-2.5 rounded-xl font-medium transition-all"
            >
              Sign out
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <div className="glass rounded-2xl p-6 space-y-3">
            <div className="flex items-center justify-between text-sm text-neutral-400">
              <span>Total Reports</span>
              <ClipboardList size={18} className="text-primary" />
            </div>
            <div className="text-3xl font-bold">
              {metrics ? metrics.total_reports : '—'}
            </div>
            <div className="text-xs text-neutral-500">All-time dispatch records</div>
          </div>

          <div className="glass rounded-2xl p-6 space-y-3">
            <div className="flex items-center justify-between text-sm text-neutral-400">
              <span>Last 24 Hours</span>
              <Activity size={18} className="text-emerald-400" />
            </div>
            <div className="text-3xl font-bold">
              {metrics ? metrics.reports_24h : '—'}
            </div>
            <div className="text-xs text-neutral-500">Recent incoming emergencies</div>
          </div>

          <div className="glass rounded-2xl p-6 space-y-3">
            <div className="flex items-center justify-between text-sm text-neutral-400">
              <span>Avg Severity</span>
              <ShieldAlert size={18} className="text-yellow-300" />
            </div>
            <div className="text-3xl font-bold">
              {avgSeverityLabel}
              <span className="text-sm text-neutral-500 ml-2">{avgSeverityScore}</span>
            </div>
            <div className="text-xs text-neutral-500">Rolling severity score</div>
          </div>

          <div className="glass rounded-2xl p-6 space-y-3">
            <div className="flex items-center justify-between text-sm text-neutral-400">
              <span>Pending Reviews</span>
              <MapPinned size={18} className="text-indigo-300" />
            </div>
            <div className="text-3xl font-bold">
              {metrics ? metrics.pending_reviews ?? 0 : '—'}
            </div>
            <div className="text-xs text-neutral-500">Human-in-the-loop queue</div>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Weekly Call Volume</h2>
              <span className="text-xs text-neutral-500">Last 7 days</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={breakdown?.by_day || []}>
                  <defs>
                    <linearGradient id="callGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ff4500" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#ff4500" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" />
                  <XAxis dataKey="date" stroke="#6b7280" fontSize={12} />
                  <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '12px' }}
                    labelStyle={{ color: '#d1d5db' }}
                  />
                  <Area type="monotone" dataKey="count" stroke="#ff4500" fill="url(#callGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Emergency Type Mix</h2>
              <span className="text-xs text-neutral-500">Last 7 days</span>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={breakdown?.by_type || []}
                    dataKey="count"
                    nameKey="type"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={4}
                  >
                    {(breakdown?.by_type || []).map((entry, index) => (
                      <Cell key={`cell-${entry.type}`} fill={pieColors[index % pieColors.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '12px' }}
                    labelStyle={{ color: '#d1d5db' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="glass rounded-2xl p-6 xl:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Tuguegarao Heatmap</h2>
              <span className="text-xs text-neutral-500">Live incident clustering</span>
            </div>
            <div className="h-[360px] rounded-2xl overflow-hidden border border-white/10">
              <MapContainer center={center} zoom={12} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {heatmap.map((point, idx) => (
                  <CircleMarker
                    key={`${point.lat}-${point.lon}-${idx}`}
                    center={[point.lat, point.lon]}
                    radius={6 + point.weight * 3}
                    pathOptions={{ color: '#ff4500', fillColor: '#ff4500', fillOpacity: 0.35 }}
                  >
                    <LeafletTooltip>
                      <div className="text-xs">
                        <div>Type: {point.type || 'N/A'}</div>
                        <div>Severity: {point.severity || 'N/A'}</div>
                      </div>
                    </LeafletTooltip>
                  </CircleMarker>
                ))}
              </MapContainer>
            </div>
          </div>

          <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Status Snapshot</h2>
              <span className="text-xs text-neutral-500">All-time</span>
            </div>
            <div className="space-y-4">
              {statusStats.length === 0 && (
                <div className="text-sm text-neutral-500">No status data yet.</div>
              )}
              {statusStats.map((item) => (
                <div key={item.status} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-neutral-300">{item.status.replace('_', ' ')}</span>
                  <span className="font-semibold text-white">{item.count}</span>
                </div>
              ))}
            </div>
            <div className="mt-6 text-xs text-neutral-500">
              {loading ? 'Refreshing...' : 'Auto-refresh every 10 seconds'}
            </div>
          </div>
        </div>

        <div className="glass rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Reports</h2>
            <button
              onClick={fetchAll}
              className="text-sm font-medium text-neutral-400 hover:text-white transition-colors"
            >
              Refresh
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-neutral-400">
                <tr>
                  <th className="text-left pb-3 font-medium">Call</th>
                  <th className="text-left pb-3 font-medium">Type</th>
                  <th className="text-left pb-3 font-medium">Severity</th>
                  <th className="text-left pb-3 font-medium">Status</th>
                  <th className="text-left pb-3 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="text-neutral-200">
                {reports.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-neutral-500">
                      No reports yet. Awaiting first dispatch.
                    </td>
                  </tr>
                )}
                {reports.map((report) => (
                  <tr key={report.id} className="border-t border-white/5">
                    <td className="py-3 font-mono text-xs text-neutral-400">{report.call_id || 'N/A'}</td>
                    <td className="py-3">{report.emergency_types || 'N/A'}</td>
                    <td className="py-3">{report.severity || 'N/A'}</td>
                    <td className="py-3 capitalize">{report.status?.replace('_', ' ') || 'N/A'}</td>
                    <td className="py-3 text-neutral-400">{formatTime(report.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
