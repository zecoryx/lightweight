import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const DATA_FILE = path.join(process.cwd(), "src/data/users.json");

// Ensure directory and file exist
const ensureFile = () => {
  const dir = path.dirname(DATA_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  if (!fs.existsSync(DATA_FILE)) {
    fs.writeFileSync(DATA_FILE, JSON.stringify([], null, 2));
  }
};

export async function POST(req: Request) {
  try {
    const data = await req.json();
    
    // Improved IP detection
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

    ensureFile();
    const fileData = fs.readFileSync(DATA_FILE, "utf-8");
    let users = JSON.parse(fileData);
    
    // Find if user already exists (Unique key: IP + GPU + OS)
    const existingIndex = users.findIndex((u: any) => 
      u.ip === newUser.ip && 
      u.gpu === newUser.gpu && 
      u.os === newUser.os
    );

    if (existingIndex !== -1) {
      // Update existing user's time
      users[existingIndex].timestamp = newUser.timestamp;
      users[existingIndex].formatted_time = newUser.formatted_time;
    } else {
      // Add new user
      users.push(newUser);
      if (users.length > 1000) users.shift();
    }

    fs.writeFileSync(DATA_FILE, JSON.stringify(users, null, 2));

    return NextResponse.json({ success: true, count: users.length });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to log user" }, { status: 500 });
  }
}

export async function GET() {
  try {
    ensureFile();
    const fileData = fs.readFileSync(DATA_FILE, "utf-8");
    const users = JSON.parse(fileData);
    return NextResponse.json({ count: users.length });
  } catch (error) {
    return NextResponse.json({ count: 10 }); // Fallback
  }
}
