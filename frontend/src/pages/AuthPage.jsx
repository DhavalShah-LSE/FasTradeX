import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function AuthPage() {
  const navigate = useNavigate();
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ full_name: '', email: '', password: '' });
  const [verifyForm, setVerifyForm] = useState({ email: '', otp: '' });
  const [message, setMessage] = useState('');
  const [messageClass, setMessageClass] = useState('');
  const [pendingEmail, setPendingEmail] = useState('');
  const [showVerify, setShowVerify] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm),
      }).then((r) => r.json());
      localStorage.setItem('ftx_access', res.access_token);
      localStorage.setItem('ftx_refresh', res.refresh_token);
      navigate('/dashboard');
    } catch (err) {
      setMessage(err.message);
      setMessageClass('error');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registerForm),
      }).then((r) => r.json());
      let text = res.message;
      if (res.dev_otp) text += ` Dev OTP: ${res.dev_otp}`;
      setPendingEmail(registerForm.email);
      setShowVerify(true);
      setMessage(text);
      setMessageClass('success');
    } catch (err) {
      setMessage(err.message);
      setMessageClass('error');
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    try {
      await fetch('/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: verifyForm.email || pendingEmail, otp: verifyForm.otp }),
      });
      setMessage('Email verified — you can log in.');
      setMessageClass('success');
    } catch (err) {
      setMessage(err.message);
      setMessageClass('error');
    }
  };

  return (
    <div className="grid grid-2">
      <section className="card">
        <h2>Log in</h2>
        <form onSubmit={handleLogin}>
          <label>Email</label>
          <input type="email" required value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} />
          <label>Password</label>
          <input type="password" required minLength="8" value={loginForm.password} onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })} />
          <button className="btn" type="submit">Login</button>
        </form>
        {message ? <p className={messageClass}>{message}</p> : null}
        <p className="muted">New here? Use the register panel or visit the plans page.</p>
      </section>
      <section className="card">
        <h2>Register</h2>
        <form onSubmit={handleRegister}>
          <label>Full name</label>
          <input required value={registerForm.full_name} onChange={(e) => setRegisterForm({ ...registerForm, full_name: e.target.value })} />
          <label>Email</label>
          <input type="email" required value={registerForm.email} onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })} />
          <label>Password (min 8 chars)</label>
          <input type="password" required minLength="8" value={registerForm.password} onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })} />
          <button className="btn secondary" type="submit">Create account</button>
        </form>
        {showVerify ? (
          <div style={{ marginTop: '1rem' }}>
            <h3>Verify email</h3>
            <form onSubmit={handleVerify}>
              <label>Email</label>
              <input type="email" value={verifyForm.email || pendingEmail} onChange={(e) => setVerifyForm({ ...verifyForm, email: e.target.value })} />
              <label>6-digit OTP</label>
              <input maxLength="6" required value={verifyForm.otp} onChange={(e) => setVerifyForm({ ...verifyForm, otp: e.target.value })} />
              <button className="btn" type="submit">Verify</button>
            </form>
          </div>
        ) : null}
      </section>
    </div>
  );
}

export default AuthPage;
