import { NextResponse } from "next/server";

// In-memory storage for Vercel/Serverless compatibility.
// Note: In serverless environments, this will reset when the function cold starts.
// For true persistence, consider using Vercel KV, Upstash Redis, or a database.
let activeUsers: any[] = [];

// Cleanup stale users (e.g., users who haven't been active in 5 minutes)
const cleanupStaleUsers = () => {
  const now = Date.now();
  const FIVE_MINUTES = 5 * 60 * 1000;
  activeUsers = activeUsers.filter(u => (now - new Date(u.timestamp).getTime()) < FIVE_MINUTES);
};

export async function POST(req: Request) {
  try {
    const data = await req.json();
    
    // Improved IP detection for Vercel
    const forwarded = req.headers.get("x-forwarded-for");
    const realIp = req.headers.get("x-real-ip");
    const ip = (forwarded ? forwarded.split(",")[0] : realIp) || "127.0.0.1";
    
    const now = new Date();
    const newUser = {
      ...data,
      ip: ip.trim(),
      timestamp: now.toISOString(),
      formatted_time: now.toLocaleString("en-US", { 
        timeZone: data.timezone || "UTC",
        dateStyle: "medium",
        timeStyle: "medium" 
      })
    };

    // Remove old entries for this user
    const existingIndex = activeUsers.findIndex((u: any) => 
      u.ip === newUser.ip && 
      u.gpu === newUser.gpu && 
      u.os === newUser.os
    );

    if (existingIndex !== -1) {
      activeUsers[existingIndex] = { ...activeUsers[existingIndex], ...newUser };
    } else {
      activeUsers.push(newUser);
    }

    // Keep memory usage low
    if (activeUsers.length > 500) activeUsers.shift();
    
    cleanupStaleUsers();

    return NextResponse.json({ success: true, count: activeUsers.length });
  } catch (error) {
    console.error("Stats API Error:", error);
    return NextResponse.json({ success: false, error: "Failed to log user" }, { status: 500 });
  }
}

export async function GET() {
  try {
    cleanupStaleUsers();
    return NextResponse.json({ count: activeUsers.length });
  } catch (error) {
    return NextResponse.json({ count: 0 }); // Default to 0 instead of 10
  }
}
