import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setAuth } from '../utils/auth';
import { motion } from 'framer-motion';

const LoginPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password
        })
      });

      if (!res.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await res.json();
      const normalizedRole = (data.role || '').toLowerCase();
      const role = normalizedRole === 'admin' ? 'admin' : 'caller';
      setAuth(role, data.token);

      if (role === 'admin') {
        navigate('/admin/command-center');
      } else {
        navigate('/');
      }
    } catch (err) {
      setError('Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-black text-white flex items-center justify-center p-6 overflow-hidden">
      {/* Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-500/20 blur-[120px] pointer-events-none" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="w-full max-w-4xl glass rounded-3xl p-8 md:p-12 grid grid-cols-1 md:grid-cols-12 gap-12 relative z-10"
      >
        <div className="md:col-span-5 flex flex-col justify-center space-y-6">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-gradient">
              Emergency Response Hub
            </h1>
            <p className="text-neutral-400 text-lg">
              Secure access portal for emergency dispatchers and callers.
            </p>
          </div>
          <div className="text-sm text-neutral-300 glass-panel rounded-xl p-4 space-y-2">
            <div className="font-semibold text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Demo Credentials
            </div>
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-neutral-400">Admin</span>
              <span className="font-mono text-xs">admin@demo.local / demo-admin</span>
            </div>
            <div className="flex justify-between items-center pt-1">
              <span className="text-neutral-400">Caller</span>
              <span className="font-mono text-xs">caller@demo.local / demo-caller</span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="md:col-span-7 flex flex-col justify-center space-y-5">
          <div className="space-y-2">
            <label className="text-sm font-medium text-neutral-300" htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@agency.gov"
              className="w-full rounded-xl bg-white/5 border border-white/10 px-5 py-4 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              required
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-neutral-300" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              className="w-full rounded-xl bg-white/5 border border-white/10 px-5 py-4 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              required
            />
          </div>
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl primary-gradient text-white shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all px-4 py-4 mt-4 font-semibold text-lg disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Authenticating...' : 'Sign In'}
          </motion.button>
          
          {error && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center"
            >
              {error}
            </motion.div>
          )}
        </form>
      </motion.div>
    </div>
  );
};

export default LoginPage;
