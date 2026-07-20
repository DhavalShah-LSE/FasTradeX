import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function PlansPage() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [message, setMessage] = useState('');
  const [messageClass, setMessageClass] = useState('');

  useEffect(() => {
    const loadPlans = async () => {
      try {
        const data = await fetch('/api/subscriptions/plans').then((r) => r.json());
        setPlans(data.plans || []);
      } catch (err) {
        setMessage(err.message);
        setMessageClass('error');
      }
    };
    loadPlans();
  }, []);

  const handleChoose = async (planKey) => {
    if (!localStorage.getItem('ftx_access')) {
      navigate('/login');
      return;
    }
    try {
      const res = await fetch('/api/subscriptions/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('ftx_access')}`,
        },
        body: JSON.stringify({ plan_key: planKey }),
      }).then((r) => r.json());
      setMessage(res.message || `Subscription updated (${res.tier || res.mode}).`);
      setMessageClass('success');
    } catch (err) {
      setMessage(err.message);
      setMessageClass('error');
    }
  };

  return (
    <div>
      <h1>Subscription plans</h1>
      <p className="muted">Without Razorpay keys, dev mode activates plans instantly for local testing.</p>
      <div className="grid grid-3">
        {plans.map((plan) => (
          <section key={plan.plan_key} className="card">
            <h3>{plan.name}</h3>
            <p className="big">₹{plan.price_inr}</p>
            <p className="muted">{plan.billing_period}</p>
            <button className="btn" type="button" onClick={() => handleChoose(plan.plan_key)}>
              Choose
            </button>
          </section>
        ))}
      </div>
      {message ? <p className={messageClass}>{message}</p> : null}
    </div>
  );
}

export default PlansPage;
