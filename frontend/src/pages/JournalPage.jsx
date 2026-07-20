import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function JournalPage() {
  const navigate = useNavigate();
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState('Loading…');
  const [message, setMessage] = useState('');
  const [messageClass, setMessageClass] = useState('');
  const [form, setForm] = useState({
    strike: '',
    option_type: 'CE',
    entry_premium: '',
    lots: '1',
    signal_score: '',
    max_pain: '',
    emotion: 'calm',
    followed_plan: 'yes',
    trade_mode: 'real',
    notes: '',
  });

  const token = localStorage.getItem('ftx_access');

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }

    const loadTrades = async () => {
      try {
        const data = await fetch('/journal/trades?limit=50', { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json());
        setTrades(data.trades || []);
      } catch (err) {
        setTrades([]);
        setSummary(err.message);
      }

      try {
        const a = await fetch('/journal/analytics/summary', { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json());
        setSummary(`<p>Trades: <strong>${a.total_trades}</strong> • Win rate: <strong>${a.win_rate}%</strong> • Total net P&L: <strong>₹${a.total_net_pnl}</strong></p><p class='muted'>Best window: ${a.best_window || '—'} • ${a.graduation?.message || ''}</p>`);
      } catch (err) {
        setSummary(err.message);
      }
    };

    loadTrades();
  }, [navigate, token]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        strike: Number(form.strike),
        option_type: form.option_type,
        entry_premium: Number(form.entry_premium),
        lots: Number(form.lots || 1),
        emotional_state_entry: form.emotion,
        trade_mode: form.trade_mode,
        followed_plan: form.followed_plan === 'yes',
        signal_score: form.signal_score ? Number(form.signal_score) : null,
        max_pain_at_entry: form.max_pain ? Number(form.max_pain) : null,
        notes: form.notes || null,
      };
      await fetch('/journal/trade', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      setMessage('Trade logged.');
      setMessageClass('success');
      setForm({ ...form, strike: '', entry_premium: '', lots: '1', signal_score: '', max_pain: '', notes: '' });
      window.location.reload();
    } catch (err) {
      setMessage(err.message);
      setMessageClass('error');
    }
  };

  const handleExport = async () => {
    try {
      const res = await fetch('/journal/export.csv', { headers: { Authorization: `Bearer ${token}` } });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'fastradex_trades.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="grid grid-2">
      <section className="card">
        <h2>Log trade</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div>
              <label>Strike</label>
              <input name="strike" type="number" required value={form.strike} onChange={handleChange} />
            </div>
            <div>
              <label>Type</label>
              <select name="option_type" value={form.option_type} onChange={handleChange}>
                <option value="CE">CE</option>
                <option value="PE">PE</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div>
              <label>Entry premium</label>
              <input name="entry_premium" type="number" step="0.05" required value={form.entry_premium} onChange={handleChange} />
            </div>
            <div>
              <label>Lots</label>
              <input name="lots" type="number" min="1" value={form.lots} onChange={handleChange} />
            </div>
          </div>
          <div className="form-row">
            <div>
              <label>Signal score (/7)</label>
              <input name="signal_score" type="number" step="0.1" value={form.signal_score} onChange={handleChange} />
            </div>
            <div>
              <label>Max Pain at entry</label>
              <input name="max_pain" type="number" value={form.max_pain} onChange={handleChange} />
            </div>
          </div>
          <label>Emotion at entry</label>
          <select name="emotion" value={form.emotion} onChange={handleChange}>
            <option value="calm">Calm</option>
            <option value="fomo">FOMO</option>
            <option value="anxious">Anxious</option>
            <option value="confident">Confident</option>
            <option value="revenge">Revenge</option>
          </select>
          <label>Followed plan?</label>
          <select name="followed_plan" value={form.followed_plan} onChange={handleChange}>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
          <label>Mode</label>
          <select name="trade_mode" value={form.trade_mode} onChange={handleChange}>
            <option value="real">Real</option>
            <option value="paper">Paper</option>
          </select>
          <label>Notes</label>
          <textarea name="notes" rows="2" value={form.notes} onChange={handleChange} />
          <button className="btn" type="submit">Save entry</button>
        </form>
        {message ? <p className={messageClass}>{message}</p> : null}
      </section>
      <section className="card">
        <h2>Analytics</h2>
        <div className="muted" dangerouslySetInnerHTML={{ __html: summary }} />
        <button className="btn secondary" type="button" onClick={handleExport}>Export CSV</button>
        <table style={{ marginTop: '1rem' }}>
          <thead>
            <tr>
              <th>Date</th><th>Contract</th><th>Entry</th><th>Exit</th><th>Net P&amp;L</th><th>Window</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id || `${t.trade_date}-${t.strike}`}>
                <td>{t.trade_date}</td>
                <td>{t.strike} {t.option_type}</td>
                <td>{t.entry_premium}</td>
                <td>{t.exit_premium ?? '—'}</td>
                <td>{t.net_pnl != null ? `₹${t.net_pnl}` : 'Open'}</td>
                <td>{t.trading_window || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export default JournalPage;
