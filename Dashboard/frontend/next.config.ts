import type { NextConfig } from "next";
const BROKER_IP = process.env.NEXT_PUBLIC_BACKEND_IP;

const nextConfig: NextConfig = {
  
  /* 1. ALLOWED DEV ORIGINS (Root Level)
   This allows the Next.js Dev server to accept connections other machines.
   */
  allowedDevOrigins: [`${BROKER_IP}:3000`, "localhost:3000"],

  /* * 2. SERVER ACTIONS (Experimental Section)
   * This fixes the "Cross origin request detected" error when you 
   * submit forms (like login) from a different IP. 
   * Next.js checks the Host header to prevent CSRF attacks.
   */
  experimental: {
    serverActions: {
      allowedOrigins: [`${BROKER_IP}:3000`, "localhost:3000"],
    },
  },
};

export default nextConfig;
