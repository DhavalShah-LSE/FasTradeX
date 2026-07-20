import { useEffect, useState } from 'react';

const pillClass = (label) => {
  if (label === 'STRONG') return 'green';
  if (label === 'WEAK') return 'yellow';
  return 'red';
};

function DashboardPage() {
  const [timeBanner, setTimeBanner] = useState('Loading session context…');
  const [bannerClass, setBannerClass] = useState('banner window');
  const [spot, setSpot] = useState('—');
  const [spotMeta, setSpotMeta] = useState('Refreshing every 5s');
  const [signalScore, setSignalScore] = useState('—');
  const [signalLabel, setSignalLabel] = useState('—');
  const [signalRec, setSignalRec] = useState('—');
  const [maxPain, setMaxPain] = useState('—');
  const [pcr, setPcr] = useState('—');
  const [vix, setVix] = useState('—');
  const [activeWindow, setActiveWindow] = useState('—');
  const [rangeHigh, setRangeHigh] = useState('');
  const [signalList, setSignalList] = useState([]);

  useEffect(() => {
    const updateClockBanner = () => {
      const now = new Date();
      const mins = now.getHours() * 60 + now.getMinutes();
      let text = 'Outside core expiry windows — observe only.';
      let cls = 'banner window';
      if (mins >= 14 * 60 + 55) {
        text = 'STT danger window approaching — plan exits before 3:15 PM.';
        cls = 'banner stt';
      } else if (mins >= 13 * 60 + 30 && mins <= 14 * 60 + 30) {
        text = 'Expiry Rush window (Gamma Blast) — primary scalp window.';
      } else if (mins >= 9 * 60 && mins <= 10 * 60) {
        text = 'ORB window — high risk, experienced traders only.';
      }
      setTimeBanner(text);
      setBannerClass(cls);
    };

    const refreshSpot = async () => {
      try {
        const data = await fetch('/api/spot').then((r) => r.json());
        setSpot(data.spot?.toLocaleString('en-IN') ?? '—');
        setSpotMeta(`Updated ${data.updated_at || ''} • Source: ${data.source || 'n/a'}${data.message ? ` • ${data.message}` : ''}`);
      } catch (err) {
        setSpotMeta(err.message);
      }
    };

    const refreshSignals = async () => {
      try {
        const path = `/api/signals${rangeHigh ? `?range_high=${encodeURIComponent(rangeHigh)}` : ''}`;
        const data = await fetch(path).then((r) => r.json());
        setSignalScore(`${data.score} / ${data.max_score}`);
        setSignalLabel(data.label);
        setSignalRec(data.recommendation);
        setMaxPain(data.max_pain ?? '—');
        setPcr(data.pcr ?? '—');
        setVix(data.vix ?? '—');
        const entries = Object.entries(data.signals || {});
        setSignalList(entries.map(([key, val]) => ({ key, val })));
      } catch (err) {
        setSignalRec(err.message);
      }
    };

    const loadWindows = async () => {
      try {
        const data = await fetch('/api/windows').then((r) => r.json());
        setActiveWindow(data.active ? data.active.replace(/_/g, ' ') : 'None (outside defined windows)');
      } catch (_e) {
        setActiveWindow('—');
      }
    };

    updateClockBanner();
    loadWindows();
    refreshSpot();
    refreshSignals();
    const spotTimer = window.setInterval(refreshSpot, 5000);
    const signalTimer = window.setInterval(refreshSignals, 60000);
    const bannerTimer = window.setInterval(updateClockBanner, 30000);
    return () => {
      clearInterval(spotTimer);
      clearInterval(signalTimer);
      clearInterval(bannerTimer);
    };
  }, [rangeHigh]);

  return (
    <div>
      <div className={bannerClass}>{timeBanner}</div>
      <div className="grid grid-3">
        <section className="card">
          <h2>Nifty 50 Spot</h2>
          <div className="big">{spot}</div>
          <p className="muted">{spotMeta}</p>
        </section>
        <section className="card">
          <h2>7-Point Signal Score</h2>
          <div className="big">{signalScore}</div>
          <span className={`pill ${pillClass(signalLabel)}`}>{signalLabel}</span>
          <p className="muted" style={{ marginTop: '0.75rem' }}>{signalRec}</p>
          <button className="btn secondary" type="button" onClick={() => window.location.reload()}>
            Refresh now
          </button>
        </section>
        <section className="card">
          <h2>OI Context</h2>
          <p>Max Pain: <strong>{maxPain}</strong></p>
          <p>PCR: <strong>{pcr}</strong></p>
          <p>India VIX: <strong>{vix}</strong></p>
          <p className="muted">Active window: <span>{activeWindow}</span></p>
        </section>
      </div>
      <div className="grid grid-2" style={{ marginTop: '1rem' }}>
        <section className="card">
          <h3>Manual input — Range High</h3>
          <p className="muted">Mark your 5-min range high (12:00–1:30 PM) for signal #2.</p>
          <input type="number" value={rangeHigh} onChange={(e) => setRangeHigh(e.target.value)} placeholder="e.g. 24220" step="0.05" />
        </section>
        <section className="card">
          <h3>Signal checklist</h3>
          <ul className="signal-list">
            {signalList.map((item) => (
              <li key={item.key}>
                <span>{item.key.replace(/_/g, ' ')}</span>
                <span className={item.val ? 'success' : 'muted'}>{item.val ? 'Yes' : 'No'}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

export default DashboardPage;
