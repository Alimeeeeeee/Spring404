import React, { useEffect, useState } from 'react';
import SafetyMap from './SafetyMap';
import { clearToken, getMe, getToken, login, logout, saveToken, signup, verifyGender } from './authApi';
import './auth.css';

function AuthCard({ mode, setMode, onAuthenticated }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      if (mode === 'signup') {
        await signup({ email, password, nickname });
        setMode('login');
      } else {
        const result = await login({ email, password });
        saveToken(result.access_token);
        onAuthenticated(result.user);
      }
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  return <main className="auth-page"><form className="auth-card" onSubmit={submit}>
    <h1>여기지!</h1><p>안전한 귀가 경로를 추천해 드려요.</p>
    {mode === 'signup' && <input value={nickname} onChange={e=>setNickname(e.target.value)} placeholder="닉네임" required />}
    <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="이메일" required />
    <input type="password" minLength="8" value={password} onChange={e=>setPassword(e.target.value)} placeholder="비밀번호 (8자 이상)" required />
    {error && <div className="auth-error">{error}</div>}
    <button disabled={busy}>{busy ? '처리 중…' : mode === 'signup' ? '회원가입' : '로그인'}</button>
    <button type="button" className="auth-link" onClick={()=>setMode(mode === 'signup' ? 'login' : 'signup')}>
      {mode === 'signup' ? '이미 계정이 있어요' : '처음이신가요? 회원가입'}
    </button>
  </form></main>;
}

function Verify({ user, onDone, onLogout }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    try { const result = await verifyGender(code); onDone(result.user); }
    catch (err) { setError(err.message); }
  };
  return <main className="auth-page"><form className="auth-card" onSubmit={submit}>
    <h1>이용자 인증</h1><p>{user.nickname}님, MVP 테스트 코드를 입력해 주세요.</p>
    <input value={code} onChange={e=>setCode(e.target.value)} placeholder="인증 코드" required />
    {error && <div className="auth-error">{error}</div>}
    <button>인증 완료</button><button type="button" className="auth-link" onClick={onLogout}>로그아웃</button>
  </form></main>;
}

export default function App() {
  const [mode, setMode] = useState('loading');
  const [user, setUser] = useState(null);
  const route = (next) => { setUser(next); setMode(next.gender_verified ? 'map' : 'verify'); };
  const handleLogout = async () => { try { await logout(); } finally { clearToken(); setUser(null); setMode('login'); } };
  useEffect(() => {
    const expired = () => { clearToken(); setUser(null); setMode('login'); };
    window.addEventListener('hereji:session-expired', expired);
    if (getToken()) getMe().then(({user: next})=>route(next)).catch(expired);
    else setMode('login');
    return () => window.removeEventListener('hereji:session-expired', expired);
  }, []);
  if (mode === 'loading') return <main className="auth-page">불러오는 중…</main>;
  if (mode === 'login' || mode === 'signup') return <AuthCard mode={mode} setMode={setMode} onAuthenticated={route} />;
  if (mode === 'verify') return <Verify user={user} onDone={route} onLogout={handleLogout} />;
  return <SafetyMap user={user} onUserChange={setUser} onLogout={handleLogout} />;
}
