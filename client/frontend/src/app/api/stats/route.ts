import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type UserStats = {
  sessionId: string;
  timestamp: string;
};

const MAX_SESSION_ID_LENGTH = 80;
const MAX_ACTIVE_USERS = 500;
const ACTIVE_WINDOW_MS = 5 * 60 * 1000;
const KV_KEY = "lightweight:active-users";
const LOCAL_STATS_FILE = process.env.LIGHTWEIGHT_STATS_FILE;

function cleanSessionId(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const sessionId = value.trim().slice(0, MAX_SESSION_ID_LENGTH);
  return sessionId || null;
}

function cleanupStaleUsers(users: UserStats[]) {
  const now = Date.now();
  return users.filter((u) => now - new Date(u.timestamp).getTime() < ACTIVE_WINDOW_MS);
}

function parseUsers(value: unknown): UserStats[] {
  if (!Array.isArray(value)) return [];

  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const user = item as Record<string, unknown>;
    const sessionId = cleanSessionId(user.sessionId);
    if (!sessionId || typeof user.timestamp !== "string") return [];

    return [{ sessionId, timestamp: user.timestamp }];
  });
}

async function kvCommand<T>(command: unknown[]): Promise<T | null> {
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return null;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(command),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Stats KV request failed: ${res.status}`);
  }

  const data = await res.json() as { result?: T };
  return data.result ?? null;
}

async function readUsers(): Promise<UserStats[]> {
  const kvValue = await kvCommand<string>(["GET", KV_KEY]);
  if (kvValue) {
    try {
      return parseUsers(JSON.parse(kvValue));
    } catch {
      return [];
    }
  }

  try {
    const { readFile } = await import("node:fs/promises");
    const file = await readFile(getLocalStatsFile(), "utf8");
    return parseUsers(JSON.parse(file));
  } catch {
    return [];
  }
}

async function writeUsers(users: UserStats[]) {
  const payload = JSON.stringify(users);
  const kvResult = await kvCommand<string>(["SET", KV_KEY, payload]);
  if (kvResult !== null) return;

  const { mkdir, writeFile } = await import("node:fs/promises");
  const file = getLocalStatsFile();
  const dir = file.slice(0, file.lastIndexOf("/"));
  await mkdir(dir, { recursive: true });
  await writeFile(file, `${JSON.stringify(users, null, 2)}\n`, "utf8");
}

function getLocalStatsFile() {
  if (LOCAL_STATS_FILE) return LOCAL_STATS_FILE;
  if (process.env.VERCEL) return "/tmp/lightweight-active-users.json";

  return "./data/active-users.json";
}

async function getActiveUsers() {
  const users = cleanupStaleUsers(await readUsers());
  await writeUsers(users);
  return users;
}

export async function POST(req: Request) {
  try {
    const data: unknown = await req.json();
    const payload = data && typeof data === "object" ? data as Record<string, unknown> : {};
    const sessionId = cleanSessionId(payload.sessionId);

    if (!sessionId) {
      return NextResponse.json(
        { success: false, error: "Missing session id" },
        { status: 400 },
      );
    }

    const now = new Date();
    const newUser: UserStats = {
      sessionId,
      timestamp: now.toISOString(),
    };
    const activeUsers = await getActiveUsers();

    const existingIndex = activeUsers.findIndex((u) => u.sessionId === newUser.sessionId);

    if (existingIndex !== -1) {
      activeUsers[existingIndex] = { ...activeUsers[existingIndex], ...newUser };
    } else {
      activeUsers.push(newUser);
    }

    if (activeUsers.length > MAX_ACTIVE_USERS) activeUsers.shift();

    const cleanUsers = cleanupStaleUsers(activeUsers);
    await writeUsers(cleanUsers);

    return NextResponse.json({ success: true, count: cleanUsers.length });
  } catch (error) {
    console.error("Stats API Error:", error);
    return NextResponse.json({ success: false, error: "Failed to log user" }, { status: 500 });
  }
}

export async function GET() {
  try {
    const activeUsers = await getActiveUsers();
    return NextResponse.json({ count: activeUsers.length });
  } catch {
    return NextResponse.json({ count: 0 });
  }
}
