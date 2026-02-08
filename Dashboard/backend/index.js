// backend/index.js
const express = require('express');
const dotenv = require('dotenv');
const cors = require('cors');
const http = require('http'); 
const mqtt = require('mqtt');
const { Server } = require('socket.io');
const fs = require('fs'); // File System module for logging
const path = require('path'); // NEW: Path module
dotenv.config();


// --- Configuration ---
const MOCK_MODE = false; 
const ENTRY_DELAY_TIME = 10000; 
// NEW: Path to the log file. It will be created in the same folder as this script.
const LOG_FILE = path.join(__dirname, 'system_logs.json');

// --- VULNERABLE CREDENTIALS (Attack Vector #1) ---
// We hardcode these so they can be brute-forced later.
const ADMIN_USER = process.env.ADMIN_USERS;
const ADMIN_PASS = process.env.ADMIN_PASSWORD;


// Attack Vector #3 & #4: A static token allows for Session Hijacking / Replay
const STATIC_TOKEN = process.env.TOKEN;

// --- Server Setup ---
const app = express();

const PORT = 3001; // Our backend PORT
// ---- Public folder is exposed ---- 
app.use(express.static('.'));
const server = http.createServer(app); 
const io = new Server(server, {
  cors: {
    origin: "*", // Allows access from any IP (Good for hacking/testing)
    methods: ["GET", "POST"]
  }
});

// --- MQTT Setup ---
const MQTT_BROKER_IP = `mqtt://${process.env.BROKER_IP}`; 
const MQTT_PORT = 1883;
let client; 
const SENSOR_TOPICS = [
  "home/entryway/motion",
  "home/entryway/button_arm",
  "home/livingroom/button_disarm"
];

// --- In-Memory State ---
let systemState = {
  security: "DISARMED", 
  motion: "OFF", 
  fan: "OFF",
  led: "OFF",
  buzzer: "OFF"
};

// --- Timers ---
let entryDelayTimer = null;

// --- Middleware ---
app.use(cors({
    origin: '*', 
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    credentials: true
}));
app.use(express.json());

// --- ADDED: HTTP REQUEST LOGGER (Attack Vector #7) ---
// This captures EVERY request sent to the server.
// Useful for seeing brute force attempts or hijacked commands.
app.use((req, res, next) => {
    // Don't log the log-reader itself to avoid clutter
    if (req.url === '/api/logs') { next(); return; }
    
    const details = `Method: ${req.method} | URL: ${req.url} | Body: ${JSON.stringify(req.body)}`;
    // Log the IP address and the request details
    logEvent('HTTP_REQUEST', details, req.ip || 'Unknown IP');
    next();
});

// --- AUTH MIDDLEWARE (Attack Vector #4) ---
// This protects the control routes but uses a weak check.
function checkAuth(req, res, next) {
  // The vulnerability: We trust this header blindly.
  // If an attacker finds this string (sniffing), they become Admin.
  const token = req.headers['authorization'];
  
  if (token === STATIC_TOKEN) {
    next(); // Authorized!
  } else {
    console.log(`Unauthorized access attempt with token: ${token}`);
    logEvent('AUTH_FAIL', `Token denied: ${token}`, 'Unknown User');
    res.status(401).json({ success: false, message: "Unauthorized. Please Login." });
  }
}

// --- UPDATED LOGGER FUNCTION ---
// Now accepts an optional 'user' parameter to track WHO performed the action.
function logEvent(eventType, details, user = "System") {
  const timestamp = new Date().toLocaleString(); 
  const logEntry = { timestamp, user, type: eventType, details };
  
  // FIX: We now use appendFileSync. 
  // This adds the new log as a single line to the end of the file.
  // This is impossible to "overwrite" or "delete" old logs with.
  try {
    fs.appendFileSync(LOG_FILE, JSON.stringify(logEntry) + "\n");
  } catch (err) {
      console.error("Error appending to log file:", err);
  }
  
  console.log(`[LOGGED]: ${timestamp} | ${user} | ${eventType} - ${details}`);
}
// --- Helper Functions ---

// UPDATED: Added 'source' parameter to track who sent the command (Dashboard vs Logic)
function publishCommand(topic, payload, source = "System") {
  console.log(`PUBLISHING: [${topic}] ${payload}`);
  
  // Log the specific command and the source (e.g., "Web Dashboard")
  logEvent('MQTT_OUT', `Command Sent: ${topic} = ${payload}`, source);
  
  if (topic.includes('fan')) systemState.fan = payload;
  if (topic.includes('led')) systemState.led = payload;
  if (topic.includes('buzzer')) {
      systemState.buzzer = payload.includes('CHIRP') ? "OFF" : payload;
  }
  
  if (!MOCK_MODE) {
    client.publish(topic, payload);
  }
  
  io.emit('state_update', systemState);
}

function clearTimers() {
  if (entryDelayTimer) {
    console.log("Cancelling entry delay timer.");
    clearTimeout(entryDelayTimer);
    entryDelayTimer = null;
  }
}

function processMqttMessage(topic, message) {
  console.log(`PROCESSING: [${topic}] ${message}. Current State: ${systemState.security}`);

  // 1. Update basic sensor state
  if (topic === 'home/entryway/motion') {
    systemState.motion = message;
    if (message === 'ON') logEvent('SENSOR', 'Motion Detected at Entryway', 'Sensor-1'); // LOG IT
    io.emit('state_update', systemState);
  }

  // 2. Run the Security State Machine
  // UPDATED: Added source 'Automatic Logic' to publishCommand calls
  switch (systemState.security) {
    
    case "DISARMED":
      if (topic === 'home/entryway/button_arm' && message === 'PRESSED') {
        console.log("Logic: Arming system...");
        systemState.security = "ARMED";
        logEvent('SECURITY', 'System ARMED by User', 'Physical Button'); // LOG IT
        publishCommand('home/livingroom/led/set', 'ON', 'Automatic Logic'); 
        publishCommand('home/livingroom/buzzer/set', 'ARM_CHIRP', 'Automatic Logic');
      }
      break;

    case "ARMED":
      if (topic === 'home/entryway/motion' && message === 'ON') {
        console.log("Logic: Motion detected while armed. Starting entry delay.");
        systemState.security = "ENTRY_DELAY";
        logEvent('SECURITY', 'Entry Delay Started - Possible Intrusion', 'System'); // LOG IT
        publishCommand('home/livingroom/led/set', 'FAST_STROBE', 'Automatic Logic');
        publishCommand('home/livingroom/buzzer/set', 'ENTRY_BEEP', 'Automatic Logic');
        
        clearTimers(); 
        entryDelayTimer = setTimeout(triggerAlarm, ENTRY_DELAY_TIME);
      }
      if (topic === 'home/livingroom/button_disarm' && message === 'PRESSED') {
        console.log("Logic: Disarming system.");
        systemState.security = "DISARMED";
        logEvent('SECURITY', 'System DISARMED by User', 'Physical Button'); // LOG IT
        publishCommand('home/livingroom/led/set', 'OFF', 'Automatic Logic');
        publishCommand('home/livingroom/buzzer/set', 'DISARM_CHIRP', 'Automatic Logic');
      }
      break;

    case "ENTRY_DELAY":
      if (topic === 'home/livingroom/button_disarm' && message === 'PRESSED') {
        console.log("Logic: Disarmed during entry delay. Alarm cancelled.");
        clearTimers();
        systemState.security = "DISARMED";
        logEvent('SECURITY', 'System DISARMED - Alarm Cancelled', 'Physical Button'); // LOG IT
        publishCommand('home/livingroom/led/set', 'OFF', 'Automatic Logic');
        publishCommand('home/livingroom/buzzer/set', 'DISARM_CHIRP', 'Automatic Logic');
      }
      break;

    case "ALARM_TRIGGERED":
      if (topic === 'home/livingroom/button_disarm' && message === 'PRESSED') {
        console.log("Logic: Disarmed during alarm.");
        systemState.security = "DISARMED";
        logEvent('SECURITY', 'System DISARMED - Alarm Silenced', 'Physical Button'); // LOG IT
        publishCommand('home/livingroom/led/set', 'OFF', 'Automatic Logic');
        publishCommand('home/livingroom/buzzer/set', 'OFF', 'Automatic Logic');
      }
      break;
  }
  
  io.emit('state_update', systemState);
}

function triggerAlarm() {
  console.log("Logic: ENTRY DELAY EXPIRED. TRIGGERING ALARM!");
  systemState.security = "ALARM_TRIGGERED";
  logEvent('ALARM', 'ALARM TRIGGERED - Intrusion Confirmed', 'System'); // LOG IT
  publishCommand('home/livingroom/buzzer/set', 'ALARM', 'Automatic Logic');
  publishCommand('home/livingroom/led/set', 'FAST_STROBE', 'Automatic Logic'); 
  io.emit('state_update', systemState);
  entryDelayTimer = null;
}

// --- 1. MQTT Connection (or Mock Mode) ---

if (!MOCK_MODE) {
  client = mqtt.connect(MQTT_BROKER_IP, { port: MQTT_PORT, connectTimeout: 5000 });
  client.on('connect', () => {
    console.log('Connected to MQTT Broker!');
    client.subscribe(SENSOR_TOPICS, (err) => {
      if (!err) console.log('Subscribed to sensor topics:', SENSOR_TOPICS);
    });
  });
  client.on('message', (topic, payload) => {
    processMqttMessage(topic, payload.toString());
  });
  client.on('error', (err) => console.error('MQTT Connection Error:', err));

} else {
  console.log("**********************");
  console.log("Running in MOCK_MODE");
  console.log("**********************");
}

// --- 3. Express API Routes (for Dashboard Commands) ---

app.get('/api/state', (req, res) => {
  res.json(systemState);
});

// NEW: Login Route (Attack Vector #1 & #3)
// Vulnerability: Sends credentials in cleartext; Vulnerable to Brute Force
app.post('/api/login', (req, res) => {
    const { username, password } = req.body;
    console.log(`Login Attempt: ${username}:${password}`);
    console.log('HERE-------',ADMIN_USER,ADMIN_PASS);
    
    if (username === ADMIN_USER && password === ADMIN_PASS) {
        logEvent('AUTH', 'Successful Web Login', username);
        res.json({ success: true, token: STATIC_TOKEN }); //here
    } else {
        logEvent('AUTH', `Failed Login Attempt: ${username}`, 'Unknown');
        res.status(401).json({ success: false, message: "Invalid Credentials" });
    }
});

// NEW: Log Access Route (Attack Vector #7)
// Vulnerability: No checkAuth middleware! Anyone can read the logs if they guess this URL.
app.get('/api/logs', (req, res) => {
    fs.readFile(LOG_FILE, 'utf8', (err, data) => {
      if (err) return res.json([]);
      res.json(JSON.parse(data));
    });
});

// --- PROTECTED ROUTES (Require Auth) ---
// These require the STATIC_TOKEN to work.
// UPDATED: Added 'Web Dashboard' as the source for all manual commands

app.post('/api/fan', checkAuth, (req, res) => {
  const { state } = req.body; 
  if (state) {
    publishCommand('home/livingroom/fan/set', state, 'Web Dashboard');
    res.json({ success: true, state });
  } else {
    res.status(400).json({ success: false, message: 'Invalid state' });
  }
});

app.post('/api/led', checkAuth, (req, res) => {
  const { state } = req.body; 
  if (state) {
    publishCommand('home/livingroom/led/set', state, 'Web Dashboard');
    res.json({ success: true, state });
  } else {
    res.status(400).json({ success: false, message: 'Invalid state' });
  }
});

app.post('/api/buzzer', checkAuth, (req, res) => {
    const { state } = req.body;
    if (state) {
      publishCommand('home/livingroom/buzzer/set', state, 'Web Dashboard');
      res.json({ success: true, state });
    } else {
      res.status(400).json({ success: false, message: 'Invalid state' });
    }
});

// --- Mock Routes (Protected) ---
app.post('/api/mock/motion', checkAuth, (req, res) => {
  console.log("--- MOCK API: Motion Triggered ---");
  logEvent('SIMULATION', 'Motion Simulated via Dashboard', 'Web Dashboard');
  processMqttMessage('home/entryway/motion', 'ON');
  setTimeout(() => {
    console.log("--- MOCK API: Motion Reset ---");
    processMqttMessage('home/entryway/motion', 'OFF');
  }, 3000);
  res.json({ success: true });
});

app.post('/api/mock/arm', checkAuth, (req, res) => {
  console.log("--- MOCK API: Arm Button Pressed ---");
  logEvent('SIMULATION', 'Arm Button Simulated via Dashboard', 'Web Dashboard');
  processMqttMessage('home/entryway/button_arm', 'PRESSED');
  res.json({ success: true });
});

app.post('/api/mock/disarm', checkAuth, (req, res) => {
  console.log("--- MOCK API: Disarm Button Pressed ---");
  logEvent('SIMULATION', 'Disarm Button Simulated via Dashboard', 'Web Dashboard');
  processMqttMessage('home/livingroom/button_disarm', 'PRESSED');
  res.json({ success: true });
});

// --- Start the Server ---
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Backend server is running on http://localhost:${PORT}`);
});