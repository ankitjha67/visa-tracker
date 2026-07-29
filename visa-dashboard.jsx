/**
 * Visa Slot Tracker — Dashboard v4.4.0
 *
 * v4.4.0 changes vs v3.2.1:
 *   - Processor labels now cover BOTH the short portal codes the backend
 *     writes into check rows ("vfs", "bls", "us_state_dept", "page_change")
 *     and the full processor ids used in demo mode — real data used to
 *     render raw codes because only full ids were mapped.
 *   - Method badge for the US wait-time layer (us_wait_time /
 *     us_wait_time_drop).
 *   - Backend timestamps are now valid RFC3339 (the old "+00:00Z" suffix
 *     made every `new Date(found_at)` here Invalid Date — sorting and
 *     "found Xs ago" were broken for real data).
 *
 * Standalone React component. Drop into Vite/Next/CRA, or render directly via
 * Babel-standalone for a no-build setup.
 *
 * v3.2.1 changes vs v3.1:
 *   - Confidence-aware slot rendering: high/medium/low slots are visually
 *     distinct, low can be filtered out, high is grouped at the top.
 *   - Per-processor health bars (replaces per-country in v3.1) — clearer
 *     since most users have ~5 processors but 70 countries.
 *   - JWT-replay slot indicator: `method === "api_jwt"` slots get a small
 *     badge so you can see which countries the lift-api path is working for.
 *   - Tightened color tokens — fewer accent colors, clearer hierarchy.
 *   - Filter bar: confidence multi-select + processor multi-select + search.
 *
 * Connectivity strategy:
 *   1. WebSocket: ws://localhost:8081 (live feed)
 *   2. HTTP poll fallback: http://localhost:8080/api/{slots,checks,stats}
 *   3. Demo simulator (when both above fail) — generates synthetic events
 *      so you can see the UI working without a backend.
 */

import React, { useEffect, useMemo, useReducer, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownUp,
  BellRing,
  CheckCircle2,
  ChevronDown,
  Circle,
  Filter,
  Globe,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Volume2,
  VolumeX,
  Wifi,
  WifiOff,
  XCircle,
  Zap,
} from "lucide-react";

// ────────────────────────────────────────────────────────────────────────────
//  Configuration
// ────────────────────────────────────────────────────────────────────────────

const HTTP_BASE = "http://localhost:8080";
const WS_URL = "ws://localhost:8081";
const HTTP_POLL_INTERVAL_MS = 8000;
const RECONNECT_BACKOFF_MS = [1000, 2000, 4000, 8000, 15000];

// Confidence rendering tokens — ONE accent per tier, plus a neutral.
const CONF_TOKENS = {
  high: {
    label: "High",
    text: "text-emerald-200",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    ring: "ring-emerald-500/40",
    dot: "bg-emerald-400",
  },
  medium: {
    label: "Medium",
    text: "text-amber-200",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    ring: "ring-amber-500/40",
    dot: "bg-amber-400",
  },
  low: {
    label: "Low",
    text: "text-zinc-400",
    bg: "bg-zinc-500/5",
    border: "border-zinc-700",
    ring: "ring-zinc-500/30",
    dot: "bg-zinc-500",
  },
};

const PROCESSOR_LABEL = {
  // Full processor ids (registry / demo mode)
  vfs_global: "VFS",
  bls_international: "BLS",
  tls_contact: "TLS",
  cgi_federal: "CGI",
  ckgs: "CKGS",
  embassy_direct: "Embassy",
  indian_visa_online: "IVO",
  us_state_dept: "US",
  // Short portal codes the backend writes into check/slot rows
  vfs: "VFS",
  bls: "BLS",
  tls: "TLS",
  cgi: "CGI",
  embassy: "Embassy",
  ivo: "IVO",
  page_change: "Page",
  "Page Monitor": "Page",
};

// ────────────────────────────────────────────────────────────────────────────
//  State
// ────────────────────────────────────────────────────────────────────────────

const initialState = {
  slots: [],
  checks: [],
  stats: {
    total_slots: 0,
    countries: 0,
    cities: 0,
    total_checks: 0,
    error_checks: 0,
    last_check: null,
  },
  connection: "connecting", // 'connecting' | 'live' | 'polling' | 'demo' | 'paused'
  lastEventAt: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "INIT":
      return {
        ...state,
        slots: action.payload.slots ?? [],
        checks: action.payload.checks ?? [],
        stats: action.payload.stats ?? state.stats,
      };
    case "PUSH_CHECK":
      return {
        ...state,
        checks: [action.payload, ...state.checks].slice(0, 200),
        lastEventAt: new Date().toISOString(),
      };
    case "PUSH_SLOTS":
      return {
        ...state,
        slots: dedupeSlots([...action.payload, ...state.slots]).slice(0, 500),
        lastEventAt: new Date().toISOString(),
      };
    case "REPLACE_SLOTS":
      return { ...state, slots: dedupeSlots(action.payload).slice(0, 500) };
    case "REPLACE_CHECKS":
      return { ...state, checks: action.payload.slice(0, 200) };
    case "REPLACE_STATS":
      return { ...state, stats: action.payload };
    case "SET_CONNECTION":
      return { ...state, connection: action.payload };
    default:
      return state;
  }
}

function dedupeSlots(slots) {
  const seen = new Set();
  const out = [];
  for (const s of slots) {
    const key = s.uid || `${s.country}|${s.city}|${s.date}|${s.time_slot}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(s);
  }
  return out;
}

// ────────────────────────────────────────────────────────────────────────────
//  Connectivity hook
// ────────────────────────────────────────────────────────────────────────────

function useTrackerConnection(dispatch, paused) {
  const wsRef = useRef(null);
  const pollIntervalRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const demoIntervalRef = useRef(null);

  // Demo mode: generates synthetic events
  const startDemo = () => {
    if (demoIntervalRef.current) return;
    dispatch({ type: "SET_CONNECTION", payload: "demo" });
    const countries = [
      ["United Kingdom", "vfs_global", "high"],
      ["Germany", "vfs_global", "medium"],
      ["Czech Republic", "vfs_global", "high"],
      ["Spain", "bls_international", "medium"],
      ["Slovakia", "bls_international", "medium"],
      ["Portugal", "vfs_global", "medium"],
      ["Canada", "vfs_global", "high"],
      ["Japan", "vfs_global", "medium"],
    ];
    const cities = ["New Delhi", "Mumbai", "Bengaluru", "Chennai"];
    let n = 0;
    demoIntervalRef.current = setInterval(() => {
      if (paused) return;
      n++;
      const [country, processor, confidence] = countries[n % countries.length];
      const city = cities[n % cities.length];
      const status =
        Math.random() < 0.85
          ? "no_change"
          : Math.random() < 0.5
          ? "slots_found"
          : "page_changed";
      dispatch({
        type: "PUSH_CHECK",
        payload: {
          checked_at: new Date().toISOString(),
          country,
          city,
          portal: processor,
          status,
          slots_found: status === "slots_found" ? 1 + Math.floor(Math.random() * 3) : 0,
          duration_ms: 1500 + Math.floor(Math.random() * 4000),
          method: confidence === "high" ? "api_jwt" : "page_change",
          error: "",
        },
      });
      if (status === "slots_found") {
        const future = new Date(Date.now() + (10 + Math.random() * 60) * 86400000);
        dispatch({
          type: "PUSH_SLOTS",
          payload: [
            {
              uid: `demo_${n}_${Date.now()}`,
              country,
              city,
              visa_type: "Tourist",
              date: future.toISOString().slice(0, 10),
              time_slot: "10:00-11:00",
              portal: processor,
              booking_url: `https://example.invalid/${country}`,
              found_at: new Date().toISOString(),
              detection_method: confidence === "high" ? "api_jwt" : "page_change",
              confidence,
            },
          ],
        });
      }
    }, 2000);
  };

  const stopDemo = () => {
    if (demoIntervalRef.current) {
      clearInterval(demoIntervalRef.current);
      demoIntervalRef.current = null;
    }
  };

  // HTTP polling (fallback when WS fails)
  const startPolling = () => {
    if (pollIntervalRef.current) return;
    dispatch({ type: "SET_CONNECTION", payload: "polling" });
    const tick = async () => {
      try {
        const [slots, checks, stats] = await Promise.all([
          fetch(`${HTTP_BASE}/api/slots`).then((r) => r.json()),
          fetch(`${HTTP_BASE}/api/checks`).then((r) => r.json()),
          fetch(`${HTTP_BASE}/api/stats`).then((r) => r.json()),
        ]);
        dispatch({ type: "REPLACE_SLOTS", payload: slots });
        dispatch({ type: "REPLACE_CHECKS", payload: checks });
        dispatch({ type: "REPLACE_STATS", payload: stats });
      } catch (e) {
        // server vanished — fall back to demo
        stopPolling();
        startDemo();
      }
    };
    tick();
    pollIntervalRef.current = setInterval(tick, HTTP_POLL_INTERVAL_MS);
  };

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  // WebSocket primary
  const connectWs = () => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
        dispatch({ type: "SET_CONNECTION", payload: "live" });
        stopDemo();
        stopPolling();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "init") {
            dispatch({ type: "INIT", payload: msg.data });
          } else if (msg.type === "check") {
            dispatch({ type: "PUSH_CHECK", payload: msg.data });
          } else if (msg.type === "new_slots") {
            dispatch({ type: "PUSH_SLOTS", payload: msg.data.slots });
          }
        } catch (e) {
          /* ignore malformed */
        }
      };

      ws.onerror = () => {
        // server probably not running — fall through to onclose's reconnect
      };

      ws.onclose = () => {
        wsRef.current = null;
        const attempts = reconnectAttemptsRef.current;
        const delay =
          RECONNECT_BACKOFF_MS[Math.min(attempts, RECONNECT_BACKOFF_MS.length - 1)];
        reconnectAttemptsRef.current = attempts + 1;
        // After 3 failed WS attempts, try HTTP polling, then fall to demo
        if (attempts >= 3 && !pollIntervalRef.current) {
          startPolling();
        }
        if (attempts >= 6 && !demoIntervalRef.current) {
          startDemo();
          return; // stop trying WS
        }
        setTimeout(connectWs, delay);
      };
    } catch (e) {
      // WS API unavailable (e.g. SSR) — go straight to demo
      startDemo();
    }
  };

  useEffect(() => {
    if (paused) {
      dispatch({ type: "SET_CONNECTION", payload: "paused" });
      return;
    }
    connectWs();
    return () => {
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (e) {
          /* */
        }
      }
      stopPolling();
      stopDemo();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paused]);

  const triggerRunNow = async () => {
    try {
      const r = await fetch(`${HTTP_BASE}/api/run-now`, { method: "POST" });
      const j = await r.json();
      return { ok: !!j.ok, msg: j.msg || "" };
    } catch (e) {
      return { ok: false, msg: "Server unreachable — running in demo mode" };
    }
  };

  return { triggerRunNow };
}

// ────────────────────────────────────────────────────────────────────────────
//  UI helpers
// ────────────────────────────────────────────────────────────────────────────

function timeAgo(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const ms = Date.now() - d.getTime();
  const s = Math.floor(ms / 1000);
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return d.toLocaleDateString();
}

function ConnectionPill({ state }) {
  const map = {
    connecting: { Icon: Loader2, label: "Connecting", cls: "text-zinc-400 bg-zinc-800/60", spin: true },
    live: { Icon: Wifi, label: "Live", cls: "text-emerald-300 bg-emerald-500/10" },
    polling: { Icon: ArrowDownUp, label: "Polling", cls: "text-sky-300 bg-sky-500/10" },
    demo: { Icon: Circle, label: "Demo mode", cls: "text-amber-300 bg-amber-500/10" },
    paused: { Icon: Pause, label: "Paused", cls: "text-zinc-300 bg-zinc-700/60" },
  };
  const cfg = map[state] || map.connecting;
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.cls}`}>
      <cfg.Icon className={`w-3 h-3 ${cfg.spin ? "animate-spin" : ""}`} />
      <span>{cfg.label}</span>
    </div>
  );
}

function ConfidenceBadge({ confidence, size = "sm" }) {
  const t = CONF_TOKENS[confidence] || CONF_TOKENS.medium;
  const dim = size === "lg" ? "text-xs px-2 py-1" : "text-[10px] px-1.5 py-0.5";
  return (
    <span className={`inline-flex items-center gap-1 rounded ${t.bg} ${t.text} ${t.border} border ${dim} font-medium uppercase tracking-wider`}>
      <span className={`w-1.5 h-1.5 rounded-full ${t.dot}`} />
      {t.label}
    </span>
  );
}

function MethodBadge({ method }) {
  if (!method) return null;
  const map = {
    api_jwt: { label: "JWT API", cls: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30" },
    api: { label: "API", cls: "text-sky-300 bg-sky-500/10 border-sky-500/30" },
    page_change: { label: "Page", cls: "text-zinc-400 bg-zinc-800/60 border-zinc-700" },
    scrape: { label: "DOM", cls: "text-amber-300 bg-amber-500/10 border-amber-500/30" },
    us_wait_time: { label: "US Wait", cls: "text-indigo-300 bg-indigo-500/10 border-indigo-500/30" },
    us_wait_time_drop: { label: "US Drop", cls: "text-indigo-300 bg-indigo-500/10 border-indigo-500/30" },
    none: { label: "—", cls: "text-zinc-500" },
  };
  const cfg = map[method] || { label: method, cls: "text-zinc-400 bg-zinc-800/60 border-zinc-700" };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${cfg.cls} font-mono`}>
      {cfg.label}
    </span>
  );
}

function StatusIcon({ status }) {
  if (status === "slots_found")
    return <Zap className="w-3.5 h-3.5 text-emerald-400" aria-label="Slots found" />;
  if (status === "page_changed")
    return <BellRing className="w-3.5 h-3.5 text-sky-400" aria-label="Page changed" />;
  if (status === "baseline")
    return <Circle className="w-3.5 h-3.5 text-zinc-500" aria-label="Baseline stored" />;
  if (status === "captcha")
    return <ShieldAlert className="w-3.5 h-3.5 text-amber-400" aria-label="CAPTCHA" />;
  if (status === "error")
    return <XCircle className="w-3.5 h-3.5 text-red-400" aria-label="Error" />;
  if (status === "login_needed")
    return <ShieldAlert className="w-3.5 h-3.5 text-amber-400" aria-label="Login required" />;
  return <Circle className="w-3.5 h-3.5 text-zinc-700" aria-label="No change" />;
}

// ────────────────────────────────────────────────────────────────────────────
//  Sub-components
// ────────────────────────────────────────────────────────────────────────────

function StatCard({ label, value, hint, accent }) {
  const accentCls = {
    emerald: "border-l-emerald-500",
    amber: "border-l-amber-500",
    sky: "border-l-sky-500",
    zinc: "border-l-zinc-600",
  }[accent || "zinc"];
  return (
    <div className={`bg-zinc-900/50 border border-zinc-800 ${accentCls} border-l-2 rounded-md p-4`}>
      <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-medium">
        {label}
      </div>
      <div className="text-2xl font-semibold text-zinc-100 mt-1 tabular-nums">{value}</div>
      {hint && <div className="text-xs text-zinc-500 mt-0.5">{hint}</div>}
    </div>
  );
}

function FilterBar({
  filters,
  setFilters,
  processorOptions,
}) {
  const toggle = (key, val) => {
    setFilters((f) => {
      const cur = new Set(f[key]);
      cur.has(val) ? cur.delete(val) : cur.add(val);
      return { ...f, [key]: Array.from(cur) };
    });
  };
  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-zinc-900/40 border border-zinc-800 rounded-md">
      <div className="flex items-center gap-2 text-xs text-zinc-500 font-medium">
        <Filter className="w-3.5 h-3.5" /> Confidence
      </div>
      <div className="flex gap-1.5">
        {["high", "medium", "low"].map((c) => {
          const active = filters.confidence.includes(c);
          const t = CONF_TOKENS[c];
          return (
            <button
              key={c}
              type="button"
              onClick={() => toggle("confidence", c)}
              className={`text-[11px] px-2 py-1 rounded border transition ${
                active
                  ? `${t.bg} ${t.text} ${t.border}`
                  : "bg-zinc-800/40 text-zinc-500 border-zinc-800 hover:border-zinc-700"
              }`}
              aria-pressed={active}
            >
              <span className="inline-flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${active ? t.dot : "bg-zinc-700"}`} />
                {t.label}
              </span>
            </button>
          );
        })}
      </div>

      <div className="w-px h-5 bg-zinc-800" />

      <div className="flex items-center gap-2 text-xs text-zinc-500 font-medium">
        <Globe className="w-3.5 h-3.5" /> Processor
      </div>
      <div className="flex flex-wrap gap-1.5">
        {processorOptions.map((p) => {
          const active = filters.processors.includes(p);
          return (
            <button
              key={p}
              type="button"
              onClick={() => toggle("processors", p)}
              className={`text-[11px] px-2 py-1 rounded border font-mono uppercase transition ${
                active
                  ? "bg-zinc-700/60 text-zinc-100 border-zinc-600"
                  : "bg-zinc-800/40 text-zinc-500 border-zinc-800 hover:border-zinc-700"
              }`}
              aria-pressed={active}
            >
              {PROCESSOR_LABEL[p] || p}
            </button>
          );
        })}
      </div>

      <div className="ml-auto flex items-center gap-2 bg-zinc-800/40 border border-zinc-800 rounded px-2 py-1">
        <Search className="w-3.5 h-3.5 text-zinc-500" />
        <input
          type="text"
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          placeholder="Country or city…"
          className="bg-transparent text-xs text-zinc-200 outline-none w-40 placeholder:text-zinc-600"
        />
      </div>
    </div>
  );
}

function SlotsPanel({ slots, filters }) {
  const filtered = useMemo(() => {
    return slots
      .filter((s) => filters.confidence.length === 0 || filters.confidence.includes(s.confidence || "medium"))
      .filter((s) => {
        if (filters.processors.length === 0) return true;
        return filters.processors.some((p) => (s.portal || "").includes(p) || s.portal === p ||
          (PROCESSOR_LABEL[p] || "").toLowerCase() === (s.portal || "").toLowerCase());
      })
      .filter((s) => {
        if (!filters.search) return true;
        const q = filters.search.toLowerCase();
        return (
          (s.country || "").toLowerCase().includes(q) ||
          (s.city || "").toLowerCase().includes(q) ||
          (s.visa_type || "").toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        const order = { high: 0, medium: 1, low: 2 };
        const oa = order[a.confidence || "medium"] ?? 1;
        const ob = order[b.confidence || "medium"] ?? 1;
        if (oa !== ob) return oa - ob;
        return new Date(b.found_at || 0) - new Date(a.found_at || 0);
      });
  }, [slots, filters]);

  if (filtered.length === 0) {
    return (
      <div className="bg-zinc-900/40 border border-dashed border-zinc-800 rounded-md py-12 text-center">
        <Circle className="w-6 h-6 mx-auto text-zinc-700" />
        <div className="text-sm text-zinc-500 mt-2">No slots match current filters</div>
        <div className="text-xs text-zinc-600 mt-1">
          {slots.length > 0
            ? `${slots.length} total — clear filters to see all`
            : "Tracker hasn't found any slots yet"}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {filtered.map((s) => {
        const conf = s.confidence || "medium";
        const t = CONF_TOKENS[conf];
        const isLow = conf === "low";
        return (
          <div
            key={s.uid}
            className={`flex items-stretch gap-0 rounded-md border ${t.border} ${t.bg} overflow-hidden ${isLow ? "opacity-70" : ""}`}
          >
            <div className={`w-1 ${t.dot}`} aria-hidden="true" />
            <div className="flex-1 p-3 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-zinc-100 text-sm">{s.country}</span>
                  <span className="text-zinc-500 text-xs">·</span>
                  <span className="text-zinc-400 text-sm">{s.city}</span>
                  <ConfidenceBadge confidence={conf} />
                  <MethodBadge method={s.detection_method} />
                </div>
                <div className="text-xs text-zinc-500 mt-0.5 flex items-center gap-3 flex-wrap">
                  <span className="text-zinc-300 font-mono">{s.date}</span>
                  {s.time_slot && s.time_slot !== "—" && (
                    <span className="text-zinc-500">{s.time_slot}</span>
                  )}
                  <span className="text-zinc-600">{s.visa_type}</span>
                  <span className="text-zinc-600">found {timeAgo(s.found_at)}</span>
                </div>
              </div>
              {s.booking_url && (
                <a
                  href={s.booking_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-xs text-zinc-300 bg-zinc-800/60 hover:bg-zinc-700/60 border border-zinc-700 px-3 py-1.5 rounded transition"
                >
                  Book →
                </a>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ChecksPanel({ checks, filters }) {
  const filtered = useMemo(() => {
    return checks.filter((c) => {
      if (filters.search) {
        const q = filters.search.toLowerCase();
        if (!(`${c.country} ${c.city}`.toLowerCase().includes(q))) return false;
      }
      return true;
    });
  }, [checks, filters]);

  return (
    <div className="bg-zinc-900/30 border border-zinc-800 rounded-md overflow-hidden">
      <div className="grid grid-cols-12 text-[10px] uppercase tracking-wider text-zinc-500 px-3 py-2 border-b border-zinc-800 bg-zinc-900/40 font-medium">
        <div className="col-span-1">Status</div>
        <div className="col-span-3">Country</div>
        <div className="col-span-2">City</div>
        <div className="col-span-1">Portal</div>
        <div className="col-span-1">Method</div>
        <div className="col-span-1 text-right">ms</div>
        <div className="col-span-3 text-right">When</div>
      </div>
      <div className="divide-y divide-zinc-800/60 max-h-96 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-6 text-center text-xs text-zinc-600">No checks yet</div>
        ) : (
          filtered.map((c, i) => (
            <div key={i} className="grid grid-cols-12 px-3 py-1.5 text-xs items-center hover:bg-zinc-800/30 transition">
              <div className="col-span-1">
                <StatusIcon status={c.status} />
              </div>
              <div className="col-span-3 text-zinc-200 truncate">{c.country}</div>
              <div className="col-span-2 text-zinc-400 truncate">{c.city}</div>
              <div className="col-span-1 text-zinc-500 font-mono uppercase text-[10px]">
                {PROCESSOR_LABEL[c.portal] || c.portal}
              </div>
              <div className="col-span-1">
                <MethodBadge method={c.method} />
              </div>
              <div className="col-span-1 text-right text-zinc-500 tabular-nums">
                {c.duration_ms || "—"}
              </div>
              <div className="col-span-3 text-right text-zinc-500">
                {timeAgo(c.checked_at)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ProcessorHealthPanel({ checks }) {
  const stats = useMemo(() => {
    const map = new Map();
    for (const c of checks) {
      const key = c.portal || "unknown";
      const cur = map.get(key) || { total: 0, ok: 0, error: 0, slots: 0 };
      cur.total += 1;
      if (c.status === "error") cur.error += 1;
      else if (c.status !== "captcha") cur.ok += 1;
      if (c.status === "slots_found" || c.status === "page_changed")
        cur.slots += c.slots_found || 1;
      map.set(key, cur);
    }
    return Array.from(map.entries())
      .map(([proc, s]) => ({
        proc,
        ...s,
        successRate: s.total > 0 ? s.ok / s.total : 0,
      }))
      .sort((a, b) => b.total - a.total);
  }, [checks]);

  if (stats.length === 0) {
    return (
      <div className="bg-zinc-900/30 border border-dashed border-zinc-800 rounded-md p-6 text-center text-xs text-zinc-600">
        No checks recorded yet — processor health will populate after first cycle
      </div>
    );
  }

  return (
    <div className="bg-zinc-900/30 border border-zinc-800 rounded-md p-4 space-y-3">
      {stats.map(({ proc, total, ok, error, slots, successRate }) => {
        const pct = Math.round(successRate * 100);
        const accent =
          pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
        return (
          <div key={proc} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="font-mono uppercase text-zinc-300 text-[10px] px-1.5 py-0.5 bg-zinc-800/60 border border-zinc-700 rounded">
                  {PROCESSOR_LABEL[proc] || proc}
                </span>
                <span className="text-zinc-500 tabular-nums">
                  {ok}/{total} ok
                </span>
                {error > 0 && (
                  <span className="text-red-400 tabular-nums">· {error} err</span>
                )}
                {slots > 0 && (
                  <span className="text-emerald-400 tabular-nums">· {slots} slots</span>
                )}
              </div>
              <div className="text-zinc-400 tabular-nums">{pct}%</div>
            </div>
            <div className="h-1.5 bg-zinc-800 rounded overflow-hidden">
              <div className={`h-full ${accent} transition-all`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
//  Tabs
// ────────────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "slots", label: "Slots" },
  { id: "checks", label: "Recent checks" },
  { id: "health", label: "Health" },
];

function Tabs({ active, setActive }) {
  const refs = useRef({});
  const onKey = (e) => {
    const idx = TABS.findIndex((t) => t.id === active);
    if (e.key === "ArrowRight") {
      const next = TABS[(idx + 1) % TABS.length];
      setActive(next.id);
      refs.current[next.id]?.focus();
      e.preventDefault();
    }
    if (e.key === "ArrowLeft") {
      const prev = TABS[(idx - 1 + TABS.length) % TABS.length];
      setActive(prev.id);
      refs.current[prev.id]?.focus();
      e.preventDefault();
    }
  };
  return (
    <div role="tablist" aria-label="Dashboard sections" onKeyDown={onKey} className="flex border-b border-zinc-800">
      {TABS.map((t) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            ref={(el) => (refs.current[t.id] = el)}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            type="button"
            onClick={() => setActive(t.id)}
            className={`relative px-4 py-2.5 text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 ${
              isActive ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.label}
            {isActive && (
              <span className="absolute bottom-[-1px] left-3 right-3 h-[2px] bg-emerald-500" />
            )}
          </button>
        );
      })}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
//  Toolbar
// ────────────────────────────────────────────────────────────────────────────

function Toolbar({
  connection,
  paused,
  setPaused,
  soundOn,
  setSoundOn,
  triggerRunNow,
  toast,
  setToast,
}) {
  const [pending, setPending] = useState(false);

  const onRun = async () => {
    setPending(true);
    const r = await triggerRunNow();
    setPending(false);
    setToast(r.msg || (r.ok ? "Cycle triggered" : "Trigger failed"));
    setTimeout(() => setToast(""), 3500);
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        type="button"
        onClick={onRun}
        disabled={pending}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-200 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 px-3 py-1.5 rounded transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40"
      >
        {pending ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <RefreshCw className="w-3.5 h-3.5" />
        )}
        Check now
      </button>

      <button
        type="button"
        onClick={() => setPaused((p) => !p)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-300 bg-zinc-800/60 hover:bg-zinc-700/60 border border-zinc-700 px-3 py-1.5 rounded transition focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40"
        aria-pressed={paused}
      >
        {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
        {paused ? "Resume" : "Pause"}
      </button>

      <button
        type="button"
        onClick={() => setSoundOn((s) => !s)}
        className="inline-flex items-center gap-1.5 text-xs text-zinc-300 bg-zinc-800/60 hover:bg-zinc-700/60 border border-zinc-700 px-3 py-1.5 rounded transition focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40"
        aria-pressed={soundOn}
        aria-label={soundOn ? "Mute alerts" : "Enable alert sound"}
      >
        {soundOn ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
      </button>

      <ConnectionPill state={connection} />

      {toast && (
        <div className="ml-2 text-xs text-zinc-400 bg-zinc-800/60 border border-zinc-700 rounded px-2.5 py-1">
          {toast}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
//  Root
// ────────────────────────────────────────────────────────────────────────────

export default function VisaDashboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [paused, setPaused] = useState(false);
  const [soundOn, setSoundOn] = useState(true);
  const [tab, setTab] = useState("slots");
  const [toast, setToast] = useState("");
  const [filters, setFilters] = useState({
    confidence: ["high", "medium"],   // hide low by default
    processors: [],                    // empty = all
    search: "",
  });

  const { triggerRunNow } = useTrackerConnection(dispatch, paused);

  // Sound on new high-confidence slot
  const lastSlotsCountRef = useRef(0);
  useEffect(() => {
    const newSlots = state.slots.filter((s) => s.confidence === "high");
    if (soundOn && newSlots.length > lastSlotsCountRef.current && lastSlotsCountRef.current > 0) {
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 660;
        gain.gain.setValueAtTime(0.001, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        osc.start();
        osc.stop(ctx.currentTime + 0.45);
      } catch (e) {
        /* ignore audio failures */
      }
    }
    lastSlotsCountRef.current = newSlots.length;
  }, [state.slots, soundOn]);

  const processorOptions = useMemo(() => {
    const set = new Set();
    state.checks.forEach((c) => c.portal && set.add(c.portal));
    state.slots.forEach((s) => s.portal && set.add(s.portal));
    return Array.from(set).sort();
  }, [state.checks, state.slots]);

  const highCount = state.slots.filter((s) => s.confidence === "high").length;
  const errorRate =
    state.stats.total_checks > 0
      ? Math.round((state.stats.error_checks / state.stats.total_checks) * 100)
      : 0;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-emerald-500/30">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/40 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-emerald-500/20 to-emerald-700/30 border border-emerald-500/30 grid place-items-center">
              <Activity className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight">Visa Slot Tracker</div>
              <div className="text-[11px] text-zinc-500 font-mono">v4.4.0</div>
            </div>
          </div>
          <div className="ml-auto">
            <Toolbar
              connection={state.connection}
              paused={paused}
              setPaused={setPaused}
              soundOn={soundOn}
              setSoundOn={setSoundOn}
              triggerRunNow={triggerRunNow}
              toast={toast}
              setToast={setToast}
            />
          </div>
        </div>
      </header>

      {/* Stat bar */}
      <section className="max-w-7xl mx-auto px-6 pt-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="High-conf slots"
            value={highCount}
            hint={`${state.slots.length} total active`}
            accent="emerald"
          />
          <StatCard
            label="Countries"
            value={state.stats.countries || new Set(state.slots.map((s) => s.country)).size}
            hint={`${state.stats.cities || 0} cities`}
            accent="sky"
          />
          <StatCard
            label="Total checks"
            value={state.stats.total_checks?.toLocaleString() || "0"}
            hint={`${errorRate}% error rate`}
            accent={errorRate > 50 ? "amber" : "zinc"}
          />
          <StatCard
            label="Last check"
            value={timeAgo(state.stats.last_check || state.lastEventAt)}
            hint={
              state.connection === "demo"
                ? "Demo mode — start the server to see real data"
                : state.connection === "live"
                ? "WebSocket live"
                : ""
            }
            accent="zinc"
          />
        </div>
      </section>

      {/* Filters */}
      <section className="max-w-7xl mx-auto px-6 mt-6">
        <FilterBar
          filters={filters}
          setFilters={setFilters}
          processorOptions={processorOptions}
        />
      </section>

      {/* Main */}
      <main className="max-w-7xl mx-auto px-6 mt-6 pb-12">
        <Tabs active={tab} setActive={setTab} />
        <div className="pt-4">
          {tab === "slots" && (
            <SlotsPanel slots={state.slots} filters={filters} />
          )}
          {tab === "checks" && (
            <ChecksPanel checks={state.checks} filters={filters} />
          )}
          {tab === "health" && (
            <ProcessorHealthPanel checks={state.checks} />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 mt-8">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between text-[11px] text-zinc-600">
          <span>
            {state.connection === "demo"
              ? "Demo mode — `python visa_tracker_v3.py run --server` to connect"
              : state.connection === "live"
              ? `Connected to ${WS_URL}`
              : `Polling ${HTTP_BASE}`}
          </span>
          <span className="font-mono">
            high signal first · low filtered by default · ArrowLeft/Right to switch tabs
          </span>
        </div>
      </footer>
    </div>
  );
}
