const DEFAULT_STATUS = `OpenBCI status not published yet.
POST /update with header Authorization: Bearer <STATUS_TOKEN>
and a plain text body to publish the latest analyzer output.
`;

const DEFAULT_LIVE = {
  updated_at: null,
  status_text: DEFAULT_STATUS,
  metrics: null,
  spotify: null,
  spectrum: {
    channels: [],
    frequencies_hz: [],
    median_psd: [],
    psd_by_channel: {},
  },
  stream: {
    fs_hz: null,
    window_seconds: null,
    source_samples: 0,
    returned_samples: 0,
    downsample_stride: 1,
    time_axis_seconds: [],
    eeg_uv: {},
  },
};

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "authorization,content-type",
  };
}

function textResponse(body, status = 200, extraHeaders = {}) {
  return new Response(body, {
    status,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": `public, max-age=${extraHeaders.cacheSeconds ?? 0}`,
      ...corsHeaders(),
      ...extraHeaders,
    },
  });
}

function htmlResponse(body, cacheSeconds = 0) {
  return new Response(body, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": `public, max-age=${cacheSeconds}`,
      ...corsHeaders(),
    },
  });
}

function jsonResponse(value, cacheSeconds = 0, status = 200) {
  return new Response(JSON.stringify(value, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": `public, max-age=${cacheSeconds}`,
      ...corsHeaders(),
    },
  });
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function clampLimit(url, defaultValue = 60, maxValue = 500) {
  const raw = Number(url.searchParams.get("limit") ?? defaultValue);
  if (!Number.isFinite(raw)) {
    return defaultValue;
  }
  return Math.max(1, Math.min(maxValue, Math.floor(raw)));
}

async function getLivePayload(env) {
  const stored = await env.STATUS_KV.get("latest_live_json");
  if (!stored) {
    return DEFAULT_LIVE;
  }
  try {
    return JSON.parse(stored);
  } catch {
    return {
      ...DEFAULT_LIVE,
      status_text: stored,
    };
  }
}

async function archiveSnapshot(env, payload, updatedAt, statusText) {
  if (!env.ARCHIVE_DB) {
    return;
  }
  const metrics = payload.metrics ?? {};
  const activeChannels = Array.isArray(metrics.active_channels) ? metrics.active_channels.join(",") : null;
  await env.ARCHIVE_DB.prepare(
    `INSERT INTO eeg_snapshots (
      updated_at,
      received_at,
      status_text,
      payload_json,
      paf_hz,
      alpha_theta_ratio,
      gamma_delta_ratio,
      one_over_f_slope,
      one_over_f_r2,
      artifact_flag,
      quality,
      active_channels,
      samples,
      fs_hz
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      updatedAt,
      new Date().toISOString(),
      statusText,
      JSON.stringify(payload),
      metrics.paf_hz ?? null,
      metrics.alpha_theta_ratio ?? null,
      metrics.gamma_delta_ratio ?? null,
      metrics.one_over_f_slope ?? null,
      metrics.one_over_f_r2 ?? null,
      metrics.artifact_flag ? 1 : 0,
      metrics.quality ?? null,
      activeChannels,
      metrics.samples ?? null,
      metrics.fs_hz ?? null,
    )
    .run();
}

async function getHistory(env, limit) {
  if (!env.ARCHIVE_DB) {
    return [];
  }
  const { results } = await env.ARCHIVE_DB.prepare(
    `SELECT
      id,
      updated_at,
      received_at,
      paf_hz,
      alpha_theta_ratio,
      gamma_delta_ratio,
      one_over_f_slope,
      one_over_f_r2,
      artifact_flag,
      quality,
      active_channels,
      samples,
      fs_hz
    FROM eeg_snapshots
    ORDER BY id DESC
    LIMIT ?`
  )
    .bind(limit)
    .all();
  return results ?? [];
}

async function getSpectra(env, limit) {
  if (!env.ARCHIVE_DB) {
    return [];
  }
  const { results } = await env.ARCHIVE_DB.prepare(
    `SELECT
      id,
      updated_at,
      received_at,
      payload_json,
      paf_hz,
      gamma_delta_ratio,
      one_over_f_slope,
      one_over_f_r2,
      artifact_flag,
      quality,
      active_channels,
      spectrum_channels,
      spectrum_points
    FROM spectrum_snapshots
    ORDER BY id DESC
    LIMIT ?`
  )
    .bind(limit)
    .all();
  return (results ?? []).map((item) => {
    let spotify = null;
    try {
      const payload = JSON.parse(item.payload_json);
      spotify = payload?.spotify ?? null;
    } catch {}
    return {
      ...item,
      spotify,
    };
  });
}

async function getSnapshot(env, id) {
  if (!env.ARCHIVE_DB) {
    return null;
  }
  return env.ARCHIVE_DB.prepare(
    `SELECT
      id,
      updated_at,
      received_at,
      status_text,
      payload_json
    FROM eeg_snapshots
    WHERE id = ?`
  )
    .bind(id)
    .first();
}

async function getSpectrumSnapshot(env, id) {
  if (!env.ARCHIVE_DB) {
    return null;
  }
  return env.ARCHIVE_DB.prepare(
    `SELECT
      id,
      updated_at,
      received_at,
      payload_json
    FROM spectrum_snapshots
    WHERE id = ?`
  )
    .bind(id)
    .first();
}

async function shouldArchiveSpectrum(env, updatedAt) {
  const intervalSeconds = Number(env.SPECTRUM_ARCHIVE_INTERVAL_SEC ?? "120");
  const nowMs = Date.parse(updatedAt);
  if (!Number.isFinite(nowMs)) {
    return false;
  }
  const previous = await env.STATUS_KV.get("latest_spectrum_archive_at");
  if (!previous) {
    return true;
  }
  const previousMs = Date.parse(previous);
  if (!Number.isFinite(previousMs)) {
    return true;
  }
  return (nowMs - previousMs) >= intervalSeconds * 1000;
}

async function archiveSpectrumSnapshot(env, payload, updatedAt) {
  if (!env.ARCHIVE_DB) {
    return;
  }
  const metrics = payload.metrics ?? {};
  const spectrum = payload.spectrum ?? {};
  const activeChannels = Array.isArray(metrics.active_channels) ? metrics.active_channels.join(",") : null;
  const spectrumChannels = Array.isArray(spectrum.channels) ? spectrum.channels.join(",") : null;
  const spectrumPoints = Array.isArray(spectrum.frequencies_hz) ? spectrum.frequencies_hz.length : 0;
  await env.ARCHIVE_DB.prepare(
    `INSERT INTO spectrum_snapshots (
      updated_at,
      received_at,
      payload_json,
      paf_hz,
      gamma_delta_ratio,
      one_over_f_slope,
      one_over_f_r2,
      artifact_flag,
      quality,
      active_channels,
      spectrum_channels,
      spectrum_points
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      updatedAt,
      new Date().toISOString(),
      JSON.stringify(payload),
      metrics.paf_hz ?? null,
      metrics.gamma_delta_ratio ?? null,
      metrics.one_over_f_slope ?? null,
      metrics.one_over_f_r2 ?? null,
      metrics.artifact_flag ? 1 : 0,
      metrics.quality ?? null,
      activeChannels,
      spectrumChannels,
      spectrumPoints,
    )
    .run();
  await env.STATUS_KV.put("latest_spectrum_archive_at", updatedAt);
}

function dashboardHtml() {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>OpenBCI Live</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f4f0e8;
        --panel: rgba(255, 251, 244, 0.92);
        --ink: #182229;
        --muted: #5f6d76;
        --accent: #0d6b78;
        --border: rgba(24, 34, 41, 0.12);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Helvetica Neue", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(13, 107, 120, 0.15), transparent 30rem),
          linear-gradient(180deg, #f9f6f0 0%, var(--bg) 100%);
      }
      main {
        max-width: 1080px;
        margin: 0 auto;
        padding: 24px;
      }
      h1 {
        margin: 0 0 8px;
        font-family: "IBM Plex Mono", monospace;
        font-size: clamp(1.8rem, 4vw, 3rem);
      }
      p {
        margin: 0 0 16px;
        color: var(--muted);
      }
      .grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 16px;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 16px;
        backdrop-filter: blur(14px);
        box-shadow: 0 10px 30px rgba(24, 34, 41, 0.08);
      }
      .metrics {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }
      .metric {
        padding: 12px;
        border-radius: 12px;
        background: rgba(13, 107, 120, 0.06);
      }
      .label {
        font-size: 0.8rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .value {
        margin-top: 4px;
        font-size: 1.35rem;
        font-weight: 700;
      }
      canvas {
        width: 100%;
        height: 420px;
        border-radius: 14px;
        background: linear-gradient(180deg, rgba(13, 107, 120, 0.06), rgba(24, 34, 41, 0.02));
      }
      pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.85rem;
      }
      .links {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 12px;
      }
      a {
        color: var(--accent);
        text-decoration: none;
        font-weight: 600;
      }
      .history {
        margin-top: 16px;
        max-height: 220px;
        overflow: auto;
        border-top: 1px solid var(--border);
        padding-top: 12px;
      }
      .history-item {
        padding: 8px 0;
        border-bottom: 1px solid rgba(24, 34, 41, 0.08);
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.8rem;
      }
      .artifact-yes { color: #8b1e1e; }
      .artifact-no { color: #1b6b34; }
      @media (max-width: 900px) {
        .grid { grid-template-columns: 1fr; }
        canvas { height: 320px; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>OpenBCI Cyton Live</h1>
      <p>Public stream of the latest rolling EEG window, metrics, and signal quality.</p>
      <div class="grid">
        <section class="panel">
          <canvas id="plot" width="900" height="420"></canvas>
          <div class="links">
            <a href="/live.json">live.json</a>
            <a href="/status.txt">status.txt</a>
            <a href="/status.json">status.json</a>
            <a href="/history.json">history.json</a>
            <a href="/spectra.json">spectra.json</a>
            <a href="/spectrum">spectrum page</a>
          </div>
        </section>
        <section class="panel">
          <div class="metrics" id="metrics"></div>
          <pre id="status"></pre>
          <div class="history" id="history"></div>
        </section>
      </div>
    </main>
    <script>
      const canvas = document.getElementById("plot");
      const ctx = canvas.getContext("2d");
      const metricsEl = document.getElementById("metrics");
      const statusEl = document.getElementById("status");
      const historyEl = document.getElementById("history");
      const colors = ["#0d6b78", "#d1624a", "#32744a", "#8254c6", "#9c7a1f", "#0081a7", "#5b4b8a", "#7b5f3d"];

      function metricTile(label, value, className = "") {
        return '<div class="metric"><div class="label">' + label + '</div><div class="value ' + className + '">' + value + '</div></div>';
      }

      function fmt(value, digits = 2, suffix = "") {
        if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
        return Number(value).toFixed(digits) + suffix;
      }

      function renderMetrics(payload) {
        const m = payload.metrics || {};
        metricsEl.innerHTML =
          metricTile("Updated", payload.updated_at || "n/a") +
          metricTile("PAF", fmt(m.paf_hz, 2, " Hz")) +
          metricTile("Alpha/Theta", fmt(m.alpha_theta_ratio, 2)) +
          metricTile("Gamma/Delta", fmt(m.gamma_delta_ratio, 4)) +
          metricTile("1/f Slope", fmt(m.one_over_f_slope, 2)) +
          metricTile("1/f r²", fmt(m.one_over_f_r2, 2)) +
          metricTile("Quality", m.quality || "n/a") +
          metricTile("Artifact", m.artifact_flag ? "YES" : "NO", m.artifact_flag ? "artifact-yes" : "artifact-no");
        statusEl.textContent = payload.status_text || "No live status published.";
      }

      function renderPlot(payload) {
        const stream = payload.stream || {};
        const eeg = stream.eeg_uv || {};
        const keys = Object.keys(eeg);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        if (!keys.length) {
          ctx.fillStyle = "#5f6d76";
          ctx.font = "20px IBM Plex Mono, monospace";
          ctx.fillText("Waiting for live EEG samples...", 24, 40);
          return;
        }

        const padding = 24;
        const innerWidth = canvas.width - padding * 2;
        const innerHeight = canvas.height - padding * 2;
        const rows = keys.length;
        const rowHeight = innerHeight / rows;

        ctx.strokeStyle = "rgba(24, 34, 41, 0.12)";
        ctx.lineWidth = 1;
        for (let i = 0; i <= rows; i += 1) {
          const y = padding + i * rowHeight;
          ctx.beginPath();
          ctx.moveTo(padding, y);
          ctx.lineTo(canvas.width - padding, y);
          ctx.stroke();
        }

        keys.forEach((key, index) => {
          const values = eeg[key];
          if (!values || values.length < 2) return;
          let maxAbs = 1;
          for (const value of values) {
            maxAbs = Math.max(maxAbs, Math.abs(value));
          }
          const baseline = padding + rowHeight * index + rowHeight / 2;
          ctx.strokeStyle = colors[index % colors.length];
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          values.forEach((value, sampleIndex) => {
            const x = padding + (sampleIndex / (values.length - 1)) * innerWidth;
            const y = baseline - (value / maxAbs) * (rowHeight * 0.38);
            if (sampleIndex === 0) {
              ctx.moveTo(x, y);
            } else {
              ctx.lineTo(x, y);
            }
          });
          ctx.stroke();
          ctx.fillStyle = colors[index % colors.length];
          ctx.font = "14px IBM Plex Mono, monospace";
          ctx.fillText(key.toUpperCase(), padding + 6, baseline - rowHeight * 0.36);
        });
      }

      function renderHistory(items) {
        historyEl.innerHTML = items.map((item) => {
          const paf = item.paf_hz == null ? "n/a" : Number(item.paf_hz).toFixed(2) + " Hz";
          const slope = item.one_over_f_slope == null ? "n/a" : Number(item.one_over_f_slope).toFixed(2);
          const artifact = item.artifact_flag ? "artifact" : "clean";
          return '<div class="history-item"><a href="/snapshot/' + item.id + '.json">#' + item.id + '</a> ' +
            (item.updated_at || "n/a") + ' PAF ' + paf + ' 1/f ' + slope + ' ' + artifact + '</div>';
        }).join("");
      }

      async function refresh() {
        try {
          const [liveResponse, historyResponse] = await Promise.all([
            fetch("/live.json?ts=" + Date.now(), { cache: "no-store" }),
            fetch("/history.json?limit=20&ts=" + Date.now(), { cache: "no-store" }),
          ]);
          const payload = await liveResponse.json();
          const history = await historyResponse.json();
          renderMetrics(payload);
          renderPlot(payload);
          renderHistory(history.items || []);
        } catch (error) {
          statusEl.textContent = "Fetch failed: " + error;
        }
      }

      refresh();
      setInterval(refresh, 1000);
    </script>
  </body>
</html>`;
}

function spectrumPageHtml() {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>OpenBCI Spectrum</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f4f0e8;
        --panel: rgba(255, 251, 244, 0.92);
        --ink: #182229;
        --muted: #5f6d76;
        --accent: #0d6b78;
        --border: rgba(24, 34, 41, 0.12);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Helvetica Neue", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(13, 107, 120, 0.15), transparent 30rem),
          linear-gradient(180deg, #f9f6f0 0%, var(--bg) 100%);
      }
      main {
        max-width: 1180px;
        margin: 0 auto;
        padding: 24px;
      }
      h1 {
        margin: 0 0 8px;
        font-family: "IBM Plex Mono", monospace;
        font-size: clamp(1.8rem, 4vw, 3rem);
      }
      p {
        margin: 0 0 16px;
        color: var(--muted);
      }
      .grid {
        display: grid;
        grid-template-columns: 2.2fr 1fr;
        gap: 16px;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 16px;
        backdrop-filter: blur(14px);
        box-shadow: 0 10px 30px rgba(24, 34, 41, 0.08);
      }
      canvas {
        width: 100%;
        height: 460px;
        border-radius: 14px;
        background: linear-gradient(180deg, rgba(13, 107, 120, 0.06), rgba(24, 34, 41, 0.02));
      }
      .links {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 12px;
      }
      a {
        color: var(--accent);
        text-decoration: none;
        font-weight: 600;
      }
      .summary {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin-bottom: 14px;
      }
      .metric {
        padding: 12px;
        border-radius: 12px;
        background: rgba(13, 107, 120, 0.06);
      }
      .label {
        font-size: 0.78rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .value {
        margin-top: 4px;
        font-size: 1.1rem;
        font-weight: 700;
      }
      .archive-list {
        max-height: 460px;
        overflow: auto;
        border-top: 1px solid var(--border);
        padding-top: 12px;
      }
      button {
        width: 100%;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.65);
        border-radius: 12px;
        padding: 10px 12px;
        text-align: left;
        margin-bottom: 10px;
        font: inherit;
        cursor: pointer;
      }
      button:hover {
        border-color: rgba(13, 107, 120, 0.45);
        background: rgba(13, 107, 120, 0.07);
      }
      .muted {
        color: var(--muted);
        font-size: 0.84rem;
      }
      @media (max-width: 900px) {
        .grid { grid-template-columns: 1fr; }
        canvas { height: 340px; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>OpenBCI Spectrum</h1>
      <p>Live PSD plus archived spectrum snapshots taken about every two minutes.</p>
      <div class="grid">
        <section class="panel">
          <canvas id="spectrum" width="920" height="460"></canvas>
          <div class="links">
            <a href="/">live dashboard</a>
            <a href="/live.json">live.json</a>
            <a href="/spectra.json">spectra.json</a>
          </div>
        </section>
        <section class="panel">
          <div class="summary" id="summary"></div>
          <div class="archive-list" id="archive"></div>
        </section>
      </div>
    </main>
    <script>
      const canvas = document.getElementById("spectrum");
      const ctx = canvas.getContext("2d");
      const summaryEl = document.getElementById("summary");
      const archiveEl = document.getElementById("archive");
      let selectedArchive = null;

      function fmt(value, digits = 2, suffix = "") {
        if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
        return Number(value).toFixed(digits) + suffix;
      }

      function metricTile(label, value) {
        return '<div class="metric"><div class="label">' + label + '</div><div class="value">' + value + '</div></div>';
      }

      function trackLabel(spotify) {
        if (!spotify) return "n/a";
        const artist = spotify.artist || "unknown artist";
        const track = spotify.track || "unknown track";
        return artist + " - " + track;
      }

      function eventLabel(updatedAt, spotify, prefix) {
        const timeLabel = updatedAt || "n/a";
        const track = trackLabel(spotify);
        return prefix + ": " + timeLabel + "  |  " + track;
      }

      function drawSpectrum(livePayload, archivedPayload) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const liveSpectrum = livePayload?.spectrum || {};
        const liveFreqs = liveSpectrum.frequencies_hz || [];
        const livePsd = liveSpectrum.median_psd || [];
        const archivedSpectrum = archivedPayload?.payload?.spectrum || null;
        const archivedFreqs = archivedSpectrum?.frequencies_hz || [];
        const archivedPsd = archivedSpectrum?.median_psd || [];
        const liveSpotify = livePayload?.spotify || null;
        const archivedSpotify = archivedPayload?.payload?.spotify || null;

        if (!liveFreqs.length || !livePsd.length) {
          ctx.fillStyle = "#5f6d76";
          ctx.font = "20px IBM Plex Mono, monospace";
          ctx.fillText("Waiting for spectrum data...", 24, 40);
          return;
        }

        const padding = { left: 54, right: 16, top: 56, bottom: 42 };
        const width = canvas.width - padding.left - padding.right;
        const height = canvas.height - padding.top - padding.bottom;
        const values = [...livePsd, ...archivedPsd].filter((value) => Number.isFinite(value) && value > 0);
        const yMin = Math.log10(Math.max(1e-6, Math.min(...values)));
        const yMax = Math.log10(Math.max(...values));
        const xMin = liveFreqs[0];
        const xMax = liveFreqs[liveFreqs.length - 1];

        ctx.fillStyle = "#182229";
        ctx.font = "12px IBM Plex Mono, monospace";
        ctx.fillText(eventLabel(livePayload?.updated_at, liveSpotify, "Live"), padding.left, 18);
        if (archivedPayload) {
          ctx.fillStyle = "#6e3b2f";
          ctx.fillText(eventLabel(archivedPayload?.updated_at, archivedSpotify, "Archive"), padding.left, 36);
        }

        function xOf(freq) {
          return padding.left + ((freq - xMin) / (xMax - xMin)) * width;
        }

        function yOf(psd) {
          const logValue = Math.log10(Math.max(psd, 1e-6));
          return padding.top + (1 - (logValue - yMin) / Math.max(1e-6, yMax - yMin)) * height;
        }

        ctx.strokeStyle = "rgba(24, 34, 41, 0.10)";
        ctx.lineWidth = 1;
        for (const tick of [1, 4, 8, 13, 30, 45]) {
          const x = xOf(tick);
          ctx.beginPath();
          ctx.moveTo(x, padding.top);
          ctx.lineTo(x, padding.top + height);
          ctx.stroke();
          ctx.fillStyle = "#5f6d76";
          ctx.font = "12px IBM Plex Mono, monospace";
          ctx.fillText(String(tick), x - 8, canvas.height - 14);
        }

        for (let i = 0; i <= 4; i += 1) {
          const y = padding.top + (i / 4) * height;
          ctx.beginPath();
          ctx.moveTo(padding.left, y);
          ctx.lineTo(padding.left + width, y);
          ctx.stroke();
        }

        function plotLine(freqs, psd, color, widthPx) {
          if (!freqs.length || !psd.length) return;
          ctx.strokeStyle = color;
          ctx.lineWidth = widthPx;
          ctx.beginPath();
          freqs.forEach((freq, index) => {
            const x = xOf(freq);
            const y = yOf(psd[index]);
            if (index === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          ctx.stroke();
        }

        if (archivedFreqs.length && archivedPsd.length) {
          plotLine(archivedFreqs, archivedPsd, "rgba(209, 98, 74, 0.85)", 2);
        }
        plotLine(liveFreqs, livePsd, "rgba(13, 107, 120, 0.95)", 2.5);

        ctx.fillStyle = "#0d6b78";
        ctx.font = "13px IBM Plex Mono, monospace";
        ctx.fillText("Live median PSD", padding.left + 12, padding.top + 18);
        if (archivedFreqs.length && archivedPsd.length) {
          ctx.fillStyle = "#d1624a";
          ctx.fillText("Selected archived PSD", padding.left + 160, padding.top + 18);
        }
      }

      function renderSummary(livePayload, archivedPayload, historyInfo) {
        const m = livePayload?.metrics || {};
        const archived = archivedPayload?.payload?.metrics || {};
        const liveSpotify = livePayload?.spotify || null;
        const archivedSpotify = archivedPayload?.payload?.spotify || null;
        summaryEl.innerHTML =
          metricTile("Live PAF", fmt(m.paf_hz, 2, " Hz")) +
          metricTile("Live 1/f", fmt(m.one_over_f_slope, 2)) +
          metricTile("Live track", trackLabel(liveSpotify)) +
          metricTile("Archive every", String(historyInfo.interval_seconds || 120) + " s") +
          metricTile("Archived spectra", String(historyInfo.count || 0)) +
          metricTile("Selected archive", archivedPayload ? String(archivedPayload.id) : "none") +
          metricTile("Selected track", trackLabel(archivedSpotify)) +
          metricTile("Selected PAF", archivedPayload ? fmt(archived.paf_hz, 2, " Hz") : "n/a");
      }

      function renderArchive(items) {
        archiveEl.innerHTML = items.map((item) => {
          const label = item.updated_at || "n/a";
          const spotify = item.spotify || null;
          const track = spotify ? (spotify.track || "unknown track") : "no spotify label";
          const subtitle = track + " • PAF " + fmt(item.paf_hz, 2, " Hz") + " • bins " + (item.spectrum_points || 0);
          return '<button data-id="' + item.id + '"><strong>#' + item.id + '</strong> ' + label +
            '<div class="muted">' + subtitle + '</div></button>';
        }).join("");
        archiveEl.querySelectorAll("button[data-id]").forEach((button) => {
          button.addEventListener("click", async () => {
            const id = button.getAttribute("data-id");
            const response = await fetch("/spectrum/" + id + ".json?ts=" + Date.now(), { cache: "no-store" });
            selectedArchive = await response.json();
            await refresh();
          });
        });
      }

      async function refresh() {
        const [liveResponse, spectraResponse] = await Promise.all([
          fetch("/live.json?ts=" + Date.now(), { cache: "no-store" }),
          fetch("/spectra.json?limit=20&ts=" + Date.now(), { cache: "no-store" }),
        ]);
        const livePayload = await liveResponse.json();
        const spectra = await spectraResponse.json();
        if (!selectedArchive && (spectra.items || []).length) {
          const latestId = spectra.items[0].id;
          const archivedResponse = await fetch("/spectrum/" + latestId + ".json?ts=" + Date.now(), { cache: "no-store" });
          selectedArchive = await archivedResponse.json();
        }
        renderSummary(livePayload, selectedArchive, spectra);
        renderArchive(spectra.items || []);
        drawSpectrum(livePayload, selectedArchive);
      }

      refresh();
      setInterval(refresh, 4000);
    </script>
  </body>
</html>`;
}

async function requireAuth(request, env) {
  const auth = request.headers.get("authorization") ?? "";
  return auth === `Bearer ${env.STATUS_TOKEN}`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cacheSeconds = Number(env.STATUS_CACHE_SECONDS ?? "2");

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    if (request.method === "GET" && url.pathname === "/") {
      return htmlResponse(dashboardHtml(), cacheSeconds);
    }

    if (request.method === "GET" && url.pathname === "/spectrum") {
      return htmlResponse(spectrumPageHtml(), cacheSeconds);
    }

    if (request.method === "GET" && url.pathname === "/status.txt") {
      const status = await env.STATUS_KV.get("latest_status");
      return textResponse(status ?? DEFAULT_STATUS, 200, { cacheSeconds });
    }

    if (request.method === "GET" && url.pathname === "/status.json") {
      const status = await env.STATUS_KV.get("latest_status");
      const updatedAt = await env.STATUS_KV.get("updated_at");
      return jsonResponse({ status: status ?? DEFAULT_STATUS, updated_at: updatedAt ?? null }, cacheSeconds);
    }

    if (request.method === "GET" && url.pathname === "/live.json") {
      return jsonResponse(await getLivePayload(env), cacheSeconds);
    }

    if (request.method === "GET" && url.pathname === "/history.json") {
      const limit = clampLimit(url, 60, 500);
      const items = await getHistory(env, limit);
      return jsonResponse({ items, count: items.length }, cacheSeconds);
    }

    if (request.method === "GET" && url.pathname === "/spectra.json") {
      const limit = clampLimit(url, 12, 200);
      const items = await getSpectra(env, limit);
      return jsonResponse(
        {
          items,
          count: items.length,
          interval_seconds: Number(env.SPECTRUM_ARCHIVE_INTERVAL_SEC ?? "120"),
        },
        cacheSeconds,
      );
    }

    if (request.method === "GET" && url.pathname.startsWith("/snapshot/") && url.pathname.endsWith(".json")) {
      const id = Number(url.pathname.slice("/snapshot/".length, -".json".length));
      if (!Number.isInteger(id) || id <= 0) {
        return textResponse("bad snapshot id\n", 400);
      }
      const row = await getSnapshot(env, id);
      if (!row) {
        return textResponse("not found\n", 404);
      }
      let payload;
      try {
        payload = JSON.parse(row.payload_json);
      } catch {
        payload = null;
      }
      return jsonResponse(
        {
          id: row.id,
          updated_at: row.updated_at,
          received_at: row.received_at,
          status_text: row.status_text,
          payload,
        },
        cacheSeconds,
      );
    }

    if (request.method === "GET" && url.pathname.startsWith("/spectrum/") && url.pathname.endsWith(".json")) {
      const id = Number(url.pathname.slice("/spectrum/".length, -".json".length));
      if (!Number.isInteger(id) || id <= 0) {
        return textResponse("bad spectrum id\n", 400);
      }
      const row = await getSpectrumSnapshot(env, id);
      if (!row) {
        return textResponse("not found\n", 404);
      }
      let payload;
      try {
        payload = JSON.parse(row.payload_json);
      } catch {
        payload = null;
      }
      return jsonResponse(
        {
          id: row.id,
          updated_at: row.updated_at,
          received_at: row.received_at,
          payload,
        },
        cacheSeconds,
      );
    }

    if (request.method === "POST" && url.pathname === "/update") {
      if (!(await requireAuth(request, env))) {
        return textResponse("unauthorized\n", 401);
      }

      const text = await request.text();
      const payload = text.trim() ? text : DEFAULT_STATUS;
      const now = new Date().toISOString();

      await env.STATUS_KV.put("latest_status", payload);
      await env.STATUS_KV.put("updated_at", now);
      return textResponse(`ok ${now}\n`);
    }

    if (request.method === "POST" && url.pathname === "/live") {
      if (!(await requireAuth(request, env))) {
        return textResponse("unauthorized\n", 401);
      }

      let payload;
      try {
        payload = await request.json();
      } catch {
        return textResponse("invalid json\n", 400);
      }

      const now = new Date().toISOString();
      const updatedAt = payload.updated_at ?? now;
      const statusText = payload.status_text ?? DEFAULT_STATUS;

      await env.STATUS_KV.put("latest_live_json", JSON.stringify(payload));
      await env.STATUS_KV.put("latest_status", statusText);
      await env.STATUS_KV.put("updated_at", updatedAt);
      await archiveSnapshot(env, payload, updatedAt, statusText);
      if (await shouldArchiveSpectrum(env, updatedAt)) {
        await archiveSpectrumSnapshot(env, payload, updatedAt);
      }
      return textResponse(`ok ${updatedAt}\n`);
    }

    return textResponse("not found\n", 404);
  },
};
