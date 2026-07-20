import { NavLink, useNavigate } from 'react-router-dom';

function Layout({ children }) {
  const navigate = useNavigate();
  const token = localStorage.getItem('ftx_access');

  const handleLogout = () => {
    localStorage.removeItem('ftx_access');
    localStorage.removeItem('ftx_refresh');
    navigate('/login');
  };

  return (
    <>
      <header className="topbar">
        <div className="brand">
          Fas<span>TradeX</span>
        </div>
        <nav className="nav">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/calculator">Calculator</NavLink>
          <NavLink to="/journal">Journal</NavLink>
          <NavLink to="/plans">Plans</NavLink>
          {token ? (
            <button className="btn secondary" type="button" onClick={handleLogout}>
              Logout
            </button>
          ) : (
            <NavLink to="/login">Login</NavLink>
          )}
        </nav>
      </header>
      <main className="layout">{children}</main>
      <footer className="layout disclaimer">
        Educational tool only — not SEBI-registered investment advice.
      </footer>
    </>
  );
}

export default Layout;
