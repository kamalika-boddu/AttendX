import React, { useState, useEffect } from 'react';
import LoginPage from './components/LoginPage';
import DashboardPreview from './components/DashboardPreview';
import StudentDashboard from './components/StudentDashboard';
import api, { getAuthToken } from './api/attendxApi';

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [isVerifyingSession, setIsVerifyingSession] = useState(true);
  const activeRole = currentUser ? currentUser.role : 'teacher';

  useEffect(() => {
    // Check if token exists on initial load
    const token = getAuthToken();
    if (!token) {
      setIsVerifyingSession(false);
      return;
    }

    // Verify token with backend
    api.auth.getMe()
      .then((res) => {
        if (res.success && res.user) {
          setCurrentUser(res.user);
        }
      })
      .catch(() => {
        // Token invalid or expired, clear it
        api.auth.logout();
      })
      .finally(() => {
        setIsVerifyingSession(false);
      });
  }, []);

  const handleLoginSuccess = (userData) => {
    setCurrentUser(userData);
  };

  const handleLogout = () => {
    api.auth.logout();
    setCurrentUser(null);
  };

  if (isVerifyingSession) {
    return (
      <div className="app-viewport" data-role="teacher">
        <div className="bg-glow-orb-1" aria-hidden="true" />
        <div className="bg-glow-orb-2" aria-hidden="true" />
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '80vh',
          gap: '1rem',
          color: 'var(--text-muted)'
        }}>
          <div className="loading-spinner" />
          <p style={{ fontSize: '0.9rem', letterSpacing: '0.02em' }}>
            Connecting to AttendX Cloud Service...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-viewport" data-role={activeRole}>
      {/* Background ambient gradient glow orbs */}
      <div className="bg-glow-orb-1" aria-hidden="true" />
      <div className="bg-glow-orb-2" aria-hidden="true" />

      {/* Main View Area */}
      {currentUser ? (
        currentUser.role === 'student' ? (
          <StudentDashboard user={currentUser} onLogout={handleLogout} />
        ) : (
          <DashboardPreview user={currentUser} onLogout={handleLogout} />
        )
      ) : (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </div>
  );
}
