import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { clearRole } from '../utils/auth';
import IncidentMap from './IncidentMap';

interface Hotline {
  id: number;
  name: string;
  type: string;
  contact: string;
}

interface ReviewItem {
  call_id: string;
  extracted_details: Record<string, string>;
  location?: {
    latitude?: number;
    longitude?: number;
    [key: string]: string | number | undefined;
  };
  recommended_hotlines: Hotline[];
  review_status: string;
  review_notes: string;
  updated_at: string;
}

const CommandCenter = () => {
  const [pending, setPending] = useState<Record<string, ReviewItem>>({});
  const [hotlines, setHotlines] = useState<Hotline[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOverrides, setSelectedOverrides] = useState<Record<string, number[]>>({});

  const fetchPending = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/admin/pending');
      const data = await res.json();
      if (Array.isArray(data)) {
        const pendingByCallId = data.reduce((acc: Record<string, ReviewItem>, item: ReviewItem) => {
          if (item?.call_id) acc[item.call_id] = item;
          return acc;
        }, {});
        setPending(pendingByCallId);
      } else {
        setPending(data || {});
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchHotlines = async () => {
    const res = await fetch('/api/admin/hotlines');
    const data = await res.json();
    setHotlines(data || []);
  };

  useEffect(() => {
    fetchPending();
    fetchHotlines();
    const interval = setInterval(fetchPending, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (callId: string) => {
    const overrideIds = selectedOverrides[callId] || [];
    await fetch('/api/admin/review/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        call_id: callId,
        override_hotline_ids: overrideIds.length ? overrideIds : undefined
      })
    });
    fetchPending();
  };

  const handleReject = async (callId: string) => {
    await fetch('/api/admin/review/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ call_id: callId })
    });
    fetchPending();
  };

  const toggleOverride = (callId: string, hotlineId: number) => {
    setSelectedOverrides(prev => {
      const current = prev[callId] || [];
      const next = current.includes(hotlineId)
        ? current.filter(id => id !== hotlineId)
        : [...current, hotlineId];
      return { ...prev, [callId]: next };
    });
  };

  return (
    <div className="min-h-screen bg-black text-white p-6 relative overflow-hidden">
      {/* Dynamic Backgrounds */}
      <div className="absolute top-[-10%] right-[-5%] w-[40%] h-[40%] rounded-full bg-primary/10 blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-500/10 blur-[150px] pointer-events-none" />

      <div className="max-w-7xl mx-auto space-y-8 relative z-10">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 glass rounded-2xl p-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-gradient mb-1">Command Center</h1>
            <p className="text-neutral-400 font-medium">Human-in-the-middle review queue</p>
            <p className="mt-2 text-xs text-yellow-500/70 flex items-center gap-1.5">
              <span>⚠️</span>
              <span>Simulation only — approving or rejecting here does not trigger any real-world dispatch.</span>
            </p>
          </div>
          <div className="flex gap-3">
            <Link
              to="/admin/dashboard"
              className="glass-panel hover:bg-white/10 px-5 py-2.5 rounded-xl font-medium transition-all"
            >
              Dashboard
            </Link>
            <button
              onClick={() => { clearRole(); window.location.href = '/login'; }}
              className="glass-panel hover:bg-white/10 px-6 py-2.5 rounded-xl font-medium transition-all"
            >
              Sign out
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between px-2">
          <h2 className="text-xl font-bold">Pending Reviews <span className="ml-2 text-sm px-2.5 py-0.5 rounded-full bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">{Object.keys(pending).length}</span></h2>
          <button
            onClick={fetchPending}
            className="text-sm font-medium text-neutral-400 hover:text-white transition-colors"
          >
            {loading ? 'Refreshing...' : 'Refresh Queue'}
          </button>
        </div>

        {Object.keys(pending).length === 0 && (
          <div className="glass rounded-2xl p-12 text-center border-dashed border-2 border-white/10">
            <div className="text-neutral-500 font-medium text-lg">No pending reports in the queue.</div>
            <div className="text-neutral-600 text-sm mt-2">All emergencies have been processed.</div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.entries(pending).map(([callId, item]) => (
            <div key={callId} className="glass rounded-2xl p-6 md:p-8 space-y-6 hover:shadow-[0_8px_40px_rgba(255,69,0,0.1)] transition-all border border-white/5 hover:border-primary/30 flex flex-col">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
                <div>
                  <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-1">Call ID</div>
                  <div className="font-mono text-sm text-neutral-300 bg-black/40 px-3 py-1 rounded-lg border border-white/5">{callId}</div>
                </div>
                <div className="text-sm font-semibold text-yellow-300 bg-yellow-500/10 px-3 py-1 rounded-full border border-yellow-500/30 animate-pulse">Awaiting Action</div>
              </div>

              <div className="grid grid-cols-1 gap-6 flex-1">
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Situation Summary</div>
                  <div className="text-white font-medium leading-relaxed bg-white/5 p-4 rounded-xl border border-white/5">
                    {item.extracted_details?.summary || 'N/A'}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Emergency Type</div>
                  <div className="text-red-400 font-semibold text-lg drop-shadow-[0_0_10px_rgba(248,113,113,0.3)]">
                    {item.extracted_details?.emergency_types || 'N/A'}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Location</div>
                  {item.location?.latitude != null && item.location?.longitude != null ? (
                    <IncidentMap
                      center={[item.location.latitude, item.location.longitude]}
                      zoom={15}
                      markers={[
                        {
                          lat: item.location.latitude,
                          lon: item.location.longitude,
                          type: item.extracted_details?.emergency_types
                        }
                      ]}
                      variant="single"
                      heightClassName="h-40"
                      showAttribution={false}
                    />
                  ) : (
                    <div className="text-neutral-400 font-medium bg-white/5 p-4 rounded-xl border border-white/5">
                      Location unavailable
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-3 pt-4 border-t border-white/10">
                <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Recommended Dispatch Units</div>
                <div className="flex flex-wrap gap-2">
                  {(item.recommended_hotlines || []).map(h => (
                    <span key={h.id} className="px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-sm font-medium">
                      {h.type} — {h.name}
                    </span>
                  ))}
                  {(!item.recommended_hotlines || item.recommended_hotlines.length === 0) && (
                    <span className="text-neutral-500 text-sm italic">No auto-recommendations</span>
                  )}
                </div>
              </div>

              <div className="space-y-3 pt-4 border-t border-white/10">
                <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Add Additional Units (Optional)</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {hotlines.map(h => {
                    const isChecked = (selectedOverrides[callId] || []).includes(h.id);
                    return (
                      <label key={h.id} className={`flex items-center gap-3 text-sm font-medium cursor-pointer p-3 rounded-xl border transition-all ${
                        isChecked ? 'bg-primary/20 border-primary/50 text-white' : 'bg-white/5 border-white/10 text-neutral-400 hover:bg-white/10'
                      }`}>
                        <input
                          type="checkbox"
                          className="w-4 h-4 rounded border-neutral-600 text-primary focus:ring-primary focus:ring-offset-neutral-900"
                          checked={isChecked}
                          onChange={() => toggleOverride(callId, h.id)}
                        />
                        <span className="truncate">{h.type} <span className="opacity-60">- {h.name}</span></span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-6 mt-auto">
                <button
                  onClick={() => handleApprove(callId)}
                  className="flex-1 px-4 py-3.5 rounded-xl bg-green-600/90 hover:bg-green-500 text-white font-semibold shadow-lg shadow-green-900/30 transition-all border border-green-500/50"
                >
                  Approve & Dispatch Units
                </button>
                <button
                  onClick={() => handleReject(callId)}
                  className="sm:w-1/3 px-4 py-3.5 rounded-xl glass-panel hover:bg-red-500/20 hover:border-red-500/50 hover:text-red-300 font-medium transition-all"
                >
                  Reject / Request Info
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CommandCenter;
