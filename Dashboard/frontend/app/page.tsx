'use client'; // This is CRITICAL for hooks and client-side libs
import  { useState, useEffect , SVGProps} from 'react'; 
import { io } from 'socket.io-client'; // Import the socket.io client
import { ReactNode } from 'react';

// --- CONFIGURATION ---
// Ensure this matches your Backend IP.
const BACKEND_URL = `http://${process.env.NEXT_PUBLIC_BACKEND_IP}:${process.env.NEXT_PUBLIC_BACKEND_PORT}`;

interface ControlCardProps {
  icon: ReactNode;       // Allows SVG components, JSX, or null
  title: string;
  status: string;
  statusColor: string;   // Tailwind class string (e.g., 'text-green-500')
  children: ReactNode;   // Content inside the card
}

interface FanButtonProps {
  speed: string | number;
  current: string | number;
  onClick: () => void;
  children: ReactNode;
}

interface StatusItemProps {
  icon: ReactNode;
  label: string;
  value: string | number; // Accepts "24°C" (string) or 24 (number)
  valueColor: string;     // Tailwind class string
}

// --- Icon Components  ---

const LightbulbIcon = ({ className, ...props }: SVGProps<SVGSVGElement>) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M9 18h6" /><path d="M10 22h4" />
    <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
  </svg>
);

const FanIcon = ({ className, ...props }: SVGProps<SVGSVGElement>) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10" />
    <circle cx="12" cy="12" r="3" />
    <path d="M12 15v7" /><path d="M14.6 10.5 20.7 7" /><path d="M9.4 10.5 3.3 7" />
  </svg>
);

const ShieldIcon = ({ className, ...props }: SVGProps<SVGSVGElement>) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

const BellIcon = ({ className, ...props }: SVGProps<SVGSVGElement>) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
  </svg>
);

const ZapIcon = ({ className, ...props }: SVGProps<SVGSVGElement>) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

const SirenIcon = ({ className, ...props }: SVGProps<SVGSVGElement>) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M2 9a9 9 0 0 1 9-9v3a6 6 0 0 0-6 6H2z"/><path d="M22 9a9 9 0 0 0-9-9v3a6 6 0 0 1 6 6h3z"/><path d="M18 14a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z"/><path d="M12 14v.01"/>
  </svg>
);

// --- Main App Component ---
export default function Home() {
  // --- Auth State ---
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [authToken, setAuthToken] = useState("");

  // --- System State ---
  const [systemState, setSystemState] = useState({
    security: "DISARMED",
    motion: "OFF",
    fan: "OFF",
    led: "OFF",
    buzzer: "OFF"
  });
  const [isConnected, setIsConnected] = useState(false);

  // --- Real-time WebSocket Connection ---
  useEffect(() => {
    const socket = io(BACKEND_URL);

    socket.on('connect', () => {
      console.log('Connected to backend WebSocket!');
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from backend WebSocket.');
      setIsConnected(false);
    });

    socket.on('state_update', (newState) => {
      console.log('Received state update:', newState);
      setSystemState(newState);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  // --- API Command Function (With Auth Token) ---
  const sendCommand = async (endpoint:any, payload:any) => {
    try {
      // VULNERABILITY: If 'authToken' is compromised (Session Hijacking), 
      // an attacker can send commands without knowing the password.
      const res = await fetch(`${BACKEND_URL}/api/${endpoint}`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': authToken // Attaching the token
        },
        body: JSON.stringify(payload)
      });
      
      if (res.status === 401) {
          alert("Session Expired or Unauthorized!");
          setIsLoggedIn(false);
      }
    } catch (error) {
      console.error(`Failed to send command to ${endpoint}:`, error);
    }
  };

  // --- Login Handler ---
  const handleLogin = async (e:any) => {
    e.preventDefault();
    setLoginError("");

    try {
        // VULNERABILITY: Credentials sent in cleartext JSON over HTTP.
        const res = await fetch(`${BACKEND_URL}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
       
        
        if (data.success) {
            setAuthToken(data.token);
            setIsLoggedIn(true);
        } else {
            setLoginError("Invalid credentials");
        }
    } catch (err) {
        setLoginError("Server unreachable");
    }
  };

  // --- Control Wrappers ---
  const handleToggleLight = () => {
    const newLedState = systemState.led === "OFF" ? "ON" : "OFF";
    sendCommand('led', { state: newLedState });
  };
  
  const handleSetFanSpeed = (speed:any) => {
    sendCommand('fan', { state: speed });
  };
  
  const handleToggleSecurity = () => {
    if (systemState.security === "DISARMED") {
      sendCommand('mock/arm', {});
    } else {
      sendCommand('mock/disarm', {});
    }
  };
  
  const handleSimulateMotion = () => {
    sendCommand('mock/motion', {});
  };

  // --- UI Helpers ---
  const isArmed = systemState.security !== 'DISARMED';
  const isLedOn = systemState.led !== 'OFF' && systemState.led !== 'FAST_STROBE';
  const isLedStrobing = systemState.led === 'FAST_STROBE';
  const isFanOn = systemState.fan === 'ON';
  const isBuzzerOn = systemState.buzzer === 'ALARM';
  const isMotion = systemState.motion === 'ON';
  
  const getSecurityStatus = () => {
    if (systemState.security === "ENTRY_DELAY") return "ENTRY DELAY";
    if (systemState.security === "ALARM_TRIGGERED") return "ALARM!";
    return systemState.security;
  };
  
  const getSecurityColor = () => {
    if (systemState.security === "DISARMED") return "text-green-500";
    if (systemState.security === "ARMED") return "text-cyan-400";
    if (systemState.security === "ENTRY_DELAY") return "text-yellow-400";
    return "text-red-500";
  };

  // --- CONDITIONAL RENDER: Login Screen ---
  if (!isLoggedIn) {
      return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4 font-sans">
            <div className="bg-gray-800 p-8 rounded-xl shadow-2xl w-full max-w-md border border-gray-700">
                <div className="text-center mb-8">
                    <div className="inline-block p-3 rounded-full bg-cyan-900/30 mb-4">
                        <ShieldIcon className="w-12 h-12 text-cyan-400" />
                    </div>
                    <h1 className="text-2xl font-bold text-white">Secure Access</h1>
                    <p className="text-gray-400 mt-2">Please authenticate to continue</p>
                </div>
                
                <form onSubmit={handleLogin} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-2">Username</label>
                        <input 
                            type="text" 
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full bg-gray-700 text-white p-3 rounded-lg border border-gray-600 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none transition-all"
                            placeholder="admin"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-2">Password</label>
                        <input 
                            type="password" 
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-gray-700 text-white p-3 rounded-lg border border-gray-600 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none transition-all"
                            placeholder="••••••••"
                        />
                    </div>
                    
                    {loginError && (
                        <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm text-center">
                            {loginError}
                        </div>
                    )}
                    
                    <button type="submit" className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 rounded-lg transition-all transform hover:scale-[1.02]">
                        Login
                    </button>
                </form>
                <div className="mt-6 text-center">
                    <p className="text-xs text-gray-500">
                        Protected by Basic Auth 
                    </p>
                </div>
            </div>
        </div>
      );
  }

  // --- RENDER: Dashboard (Only if Logged In) ---
  return (
    <div className="min-h-screen bg-gray-900 text-white p-4 sm:p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <header className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-cyan-400">Smart Apartment</h1>
          <div className="flex gap-4 items-center">
             <button onClick={() => setIsLoggedIn(false)} className="text-sm text-gray-400 hover:text-white">
                 Logout
             </button>
             <div className={`px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 transition-all bg-gray-800 border border-gray-700`}>
                <ShieldIcon className={`w-5 h-5 ${getSecurityColor()}`} />
                <span className={getSecurityColor()}>{getSecurityStatus()}</span>
             </div>
          </div>
        </header>
        
        {/* Connection Status Bar */}
        {!isConnected && (
           <div className="bg-red-600 border border-red-400 text-white px-4 py-3 rounded-lg relative mb-6 flex items-center justify-center gap-3">
             <strong className="font-bold">DISCONNECTED</strong>
             <span>Check Backend Connection...</span>
           </div>
        )}

        {/* Alert Bar */}
        {systemState.security === 'ALARM_TRIGGERED' && (
          <div className="bg-red-600 border border-red-400 text-white px-4 py-3 rounded-lg relative mb-6 flex items-center justify-between animate-pulse">
            <div className="flex items-center">
              <SirenIcon className="w-6 h-6 mr-3" />
              <strong className="font-bold text-lg">SECURITY ALARM!</strong>
              <span className="hidden sm:inline sm:ml-2">System has been triggered.</span>
            </div>
            <button onClick={handleToggleSecurity} className="bg-white text-red-700 font-bold py-1 px-3 rounded-full text-sm">
              Disarm
            </button>
          </div>
        )}
        
        {systemState.security === 'ENTRY_DELAY' && (
          <div className="bg-yellow-600 border border-yellow-400 text-white px-4 py-3 rounded-lg relative mb-6 flex items-center gap-3">
            <BellIcon className="w-6 h-6" />
            <strong className="font-bold">Entry Delay Active!</strong>
            <span className="hidden sm:inline">Disarm the system now.</span>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

          {/* --- Controls --- */}
          <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">
            
            {/* Security Control */}
            <ControlCard
              icon={<ShieldIcon className={`w-10 h-10 ${getSecurityColor()}`} />}
              title="Security System"
              status={getSecurityStatus()}
              statusColor={getSecurityColor()}
            >
              <button
                onClick={handleToggleSecurity}
                className={`w-full py-3 rounded-lg font-semibold text-lg transition-all ${
                  isArmed 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                {isArmed ? 'Disarm System' : 'Arm System'}
              </button>
            </ControlCard>

            {/* LED Light Control */}
            <ControlCard
              icon={<LightbulbIcon className={`w-10 h-10 ${isLedOn || isLedStrobing ? (isLedStrobing ? 'text-red-500 animate-pulse' : 'text-yellow-400') : 'text-gray-500'}`} />}
              title="Living Room Light"
              status={systemState.led.replace('_', ' ')}
              statusColor={isLedOn || isLedStrobing ? 'text-yellow-400' : 'text-gray-400'}
            >
              <button
                onClick={handleToggleLight}
                className={`w-full py-3 rounded-lg font-semibold text-lg transition-all ${
                  isLedOn
                  ? 'bg-gray-600 hover:bg-gray-700 text-white' 
                  : 'bg-yellow-500 hover:bg-yellow-600 text-gray-900'
                }`}
              >
                {isLedOn ? 'Turn Off' : 'Turn On'}
              </button>
            </ControlCard>

            {/* Fan Control */}
            <ControlCard
              icon={<FanIcon className={`w-10 h-10 ${isFanOn ? 'text-cyan-400 animate-spin-slow' : 'text-gray-500'}`} />}
              title="Living Room Fan"
              status={isFanOn ? 'ON' : 'OFF'}
              statusColor={isFanOn ? 'text-cyan-400' : 'text-gray-400'}
            >
              <div className="flex gap-2">
                <FanButton speed="OFF" current={systemState.fan} onClick={() => handleSetFanSpeed("OFF")}>Off</FanButton>
                <FanButton speed="ON" current={systemState.fan} onClick={() => handleSetFanSpeed("ON")}>On</FanButton>
              </div>
            </ControlCard>
          </div>

          {/* --- Monitors / Simulations --- */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* Sensor Status */}
            <div className="bg-gray-800 p-5 rounded-xl shadow-lg">
              <h2 className="text-xl font-semibold mb-4 text-gray-300">Sensor Status</h2>
              <div className="space-y-3">
                <StatusItem
                  icon={<SirenIcon className={`w-5 h-5 ${isMotion ? 'text-red-500' : 'text-gray-500'}`} />}
                  label="Entryway Motion"
                  value={isMotion ? 'DETECTED' : 'Clear'}
                  valueColor={isMotion ? 'text-red-500' : 'text-green-500'}
                />
                <StatusItem
                  icon={<ZapIcon className={`w-5 h-5 ${isBuzzerOn ? 'text-red-500 animate-pulse' : 'text-gray-500'}`} />}
                  label="Alarm Buzzer"
                  value={systemState.buzzer.replace('_', ' ')}
                  valueColor={isBuzzerOn ? 'text-red-500' : 'text-gray-400'}
                />
              </div>
            </div>

            {/* Sensor Simulator */}
            <div className="bg-gray-800 p-5 rounded-xl shadow-lg">
              <h2 className="text-xl font-semibold mb-4 text-gray-300">Simulator</h2>
              <p className="text-sm text-gray-400 mb-4">
                Use these buttons to simulate sensor events for testing.
              </p>
              <div className="space-y-3">
                <button
                  onClick={handleSimulateMotion}
                  disabled={isMotion}
                  className="w-full bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-all"
                >
                  Simulate Motion
                </button>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}

// --- UI Sub-Components ---
const ControlCard = ({ icon, title, status, statusColor, children }:ControlCardProps) => (
  <div className="bg-gray-800 p-5 rounded-xl shadow-lg flex flex-col justify-between">
    <div>
      <div className="flex justify-between items-start mb-3">
        {icon}
        <span className={`font-semibold text-sm ${statusColor}`}>{status}</span>
      </div>
      <h2 className="text-xl font-semibold mb-4 text-gray-200">{title}</h2>
    </div>
    <div>{children}</div>
  </div>
);

const FanButton = ({ speed, current, onClick, children }:FanButtonProps) => (
  <button
    onClick={onClick}
    className={`flex-1 py-2 rounded-md font-medium text-sm transition-all ${
      current === speed
        ? 'bg-cyan-500 text-white'
        : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
    }`}
  >
    {children}
  </button>
);

const StatusItem = ({ icon, label, value, valueColor }:StatusItemProps) => (
  <div className="flex justify-between items-center bg-gray-700/50 p-3 rounded-lg">
    <div className="flex items-center gap-3">
      {icon}
      <span className="text-gray-300">{label}</span>
    </div>
    <span className={`font-semibold text-sm ${valueColor}`}>{value}</span>
  </div>
);