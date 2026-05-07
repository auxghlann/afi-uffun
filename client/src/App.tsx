import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import CallInterface from './components/CallInterface'
import LoginPage from './components/LoginPage'
import CommandCenter from './components/CommandCenter'
import AdminDashboard from './components/AdminDashboard'
import { getRole } from './utils/auth'

const ProtectedRoute = ({ role, children }: { role: 'caller' | 'admin', children: React.ReactNode }) => {
  const currentRole = getRole();
  if (currentRole !== role) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute role="caller">
              <CallInterface />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute role="admin">
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/command-center"
          element={
            <ProtectedRoute role="admin">
              <CommandCenter />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
