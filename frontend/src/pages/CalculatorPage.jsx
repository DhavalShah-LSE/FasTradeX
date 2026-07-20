import { useEffect, useState } from 'react';

const LOT = 75;
const BROKERAGE = 40;
const OTHER = 12;

function calcStt(strike, exitPremium, niftyExit, optionType, isExpiry) {
  const premiumValue = exitPremium * LOT;
  if (!isExpiry || niftyExit == null) return 0.001 * premiumValue;
  if (optionType === 'CE' && niftyExit > strike) return 0.00125 * niftyExit * LOT;
  if (optionType === 'PE' && niftyExit < strike) return 0.00125 * niftyExit * LOT;
  return 0.001 * premiumValue;
}

function CalculatorPage() {
  const [capital, setCapital] = useState('10000');
  const [lots, setLots] = useState('1');
  const [strike, setStrike] = useState('24150');
  const [optionType, setOptionType] = useState('CE');
  const [entryPremium, setEntryPremium] = useState('30');
  const [exitPremium, setExitPremium] = useState('45');
  const [niftyExit, setNiftyExit] = useState('24220');
  const [results, setResults] = useState({ gross: '—', stt: '—', net: '—', netPct: '—' });
  const [buckets, setBuckets] = useState({ trading: '—', reserve: '—', buffer: '—', risk: '—' });
  const [flag, setFlag] = useState('');
  const [flagClass, setFlagClass] = useState('muted');

  useEffect(() => {
    const capitalNum = Number(capital || 0);
    const entry = Number(entryPremium || 0);
    const exit = Number(exitPremium || 0);
    const strikeNum = Number(strike || 0);
    const niftyExitNum = Number(niftyExit || 0);
    const lotsNum = Number(lots || 1);

    const gross = (exit - entry) * lotsNum * LOT;
    const stt = calcStt(strikeNum, exit, niftyExitNum || null, optionType, true);
    const net = gross - stt - BROKERAGE - OTHER;
    const deployed = entry * LOT * lotsNum;
    const netPct = deployed ? (net / deployed) * 100 : 0;

    setResults({
      gross: `₹${gross.toFixed(2)}`,
      stt: `₹${stt.toFixed(2)}`,
      net: `₹${net.toFixed(2)}`,
      netPct: `${netPct.toFixed(2)}%`,
    });

    setBuckets({
      trading: `₹${(capitalNum * 0.6).toFixed(0)}`,
      reserve: `₹${(capitalNum * 0.3).toFixed(0)}`,
      buffer: `₹${(capitalNum * 0.1).toFixed(0)}`,
      risk: `₹${(capitalNum * 0.05).toFixed(0)}`,
    });

    const lotCost = entry * LOT;
    if (capitalNum && lotCost > capitalNum * 0.25) {
      setFlag('RED: ATM premium exceeds 25% of capital — reduce size or skip.');
      setFlagClass('error');
    } else {
      setFlag('Premium within capital guardrails.');
      setFlagClass('success');
    }
  }, [capital, lots, strike, optionType, entryPremium, exitPremium, niftyExit]);

  return (
    <div className="grid grid-2">
      <section className="card">
        <h2>Trade P&amp;L + STT</h2>
        <form>
          <div className="form-row">
            <div>
              <label>Total capital (₹)</label>
              <input type="number" value={capital} onChange={(e) => setCapital(e.target.value)} />
            </div>
            <div>
              <label>Lots</label>
              <input type="number" min="1" value={lots} onChange={(e) => setLots(e.target.value)} />
            </div>
          </div>
          <div className="form-row">
            <div>
              <label>Strike</label>
              <input type="number" value={strike} onChange={(e) => setStrike(e.target.value)} />
            </div>
            <div>
              <label>Option type</label>
              <select value={optionType} onChange={(e) => setOptionType(e.target.value)}>
                <option value="CE">CE</option>
                <option value="PE">PE</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div>
              <label>Entry premium</label>
              <input type="number" step="0.05" value={entryPremium} onChange={(e) => setEntryPremium(e.target.value)} />
            </div>
            <div>
              <label>Exit premium</label>
              <input type="number" step="0.05" value={exitPremium} onChange={(e) => setExitPremium(e.target.value)} />
            </div>
          </div>
          <label>Nifty at exit (for ITM STT)</label>
          <input type="number" step="0.05" value={niftyExit} onChange={(e) => setNiftyExit(e.target.value)} />
        </form>
        <p className={flagClass}>{flag}</p>
        <p>Gross P&amp;L: <strong>{results.gross}</strong></p>
        <p>STT: <strong>{results.stt}</strong></p>
        <p>Net P&amp;L (after ₹40 brokerage + ₹12 fees): <strong>{results.net}</strong></p>
        <p>Return on premium deployed: <strong>{results.netPct}</strong></p>
      </section>
      <section className="card">
        <h2>₹10K survival buckets</h2>
        <p>Trading (60%): <strong>{buckets.trading}</strong></p>
        <p>Reserve (30%): <strong>{buckets.reserve}</strong></p>
        <p>Cost buffer (10%): <strong>{buckets.buffer}</strong></p>
        <p>Max risk per trade (5%): <strong>{buckets.risk}</strong></p>
        <p className="muted">Golden rule: never hold ITM into the 3:20 PM close on expiry.</p>
      </section>
    </div>
  );
}

export default CalculatorPage;
