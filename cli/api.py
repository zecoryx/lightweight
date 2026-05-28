import os
import time
import logging
import asyncio
import json
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from collections import OrderedDict

# Package relative imports for EXE stability
from .inference import InferenceEngine
from .models import ModelManager
from .hardware import Detector
from .strategy import StrategyEngine
from .metadata import read_model_metadata
from .runtime_policy import apply_metadata

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LightWeightAPI")

app = FastAPI(title="LightWeight Production API")
inference_lock = asyncio.Lock()

# LRU Cache
class EngineCache:
    def __init__(self, capacity: int = 2):
        self.cache = OrderedDict()
        self.capacity = capacity
    def get(self, key: str):
        if key not in self.cache: return None
        self.cache.move_to_end(key); return self.cache[key]
    def put(self, key: str, value: InferenceEngine):
        if key in self.cache: self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            old_key, old_engine = self.cache.popitem(last=False)
            if hasattr(old_engine, 'mem_manager'): old_engine.mem_manager.compact(old_engine.model)

engine_cache = EngineCache(capacity=1) # 4GB RAM uchun xavfsizroq

def _chat_ui_path() -> Path:
    return Path(__file__).resolve().parents[1] / "client" / "chat-ui" / "index.html"

def _load_chat_html() -> str:
    try:
        return _chat_ui_path().read_text(encoding="utf-8")
    except OSError:
        return CHAT_HTML

def _apply_runtime_profile(strategy, profile: Optional[dict]):
    if not profile:
        return strategy
    if "n_gpu_layers" in profile:
        strategy.n_gpu_layers = max(0, int(profile["n_gpu_layers"]))
    if "n_batch" in profile:
        strategy.n_batch = max(1, int(profile["n_batch"]))
    if "n_ubatch" in profile:
        strategy.n_ubatch = max(1, int(profile["n_ubatch"]))
    if "n_threads" in profile:
        strategy.n_threads = max(1, int(profile["n_threads"]))
    if "n_threads_batch" in profile:
        strategy.n_threads_batch = max(1, int(profile["n_threads_batch"]))
    if "ctx" in profile:
        strategy.n_ctx = max(1, int(profile["ctx"]))
    if "kv_cache_type" in profile:
        strategy.kv_cache_type = str(profile["kv_cache_type"])
    if "moe_offload" in profile:
        strategy.moe_offload = str(profile["moe_offload"])
    if "n_cpu_moe" in profile and profile["n_cpu_moe"] is not None:
        strategy.n_cpu_moe = max(0, int(profile["n_cpu_moe"]))
    return strategy

def _apply_squeeze_profile(strategy, profile: Optional[dict]):
    if not profile:
        return strategy
    if profile.get("ctx"):
        strategy.n_ctx = max(128, int(profile["ctx"]))
    if profile.get("active_set"):
        strategy.active_set_policy = str(profile["active_set"])
    if "ssd" in str(profile.get("memory_tier", "")).lower():
        strategy.ssd_policy = "fallback-only"
    if "moe" in str(profile.get("active_set", "")).lower():
        strategy.use_expert_offloading = True
        if strategy.moe_offload == "off":
            strategy.moe_offload = "first-n"
    return strategy

CHAT_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LightWeight Chat</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f3eb;
      --panel: #fffaf2;
      --text: #24201a;
      --muted: #7b7166;
      --line: #e7dccf;
      --accent: #111111;
      --assistant: #ffffff;
      --user: #ece4d8;
      --control: #fffdf8;
      --hover: #efe5d8;
      --danger: #9f2f24;
      --composer-fade: rgba(247,243,235,0);
    }
    [data-theme="dark"] {
      color-scheme: dark;
      --bg: #262625;
      --panel: #343331;
      --text: #f1eee8;
      --muted: #aaa39a;
      --line: #464541;
      --accent: #d97757;
      --assistant: #2d2c2a;
      --user: #343331;
      --control: #343331;
      --hover: #3d3c39;
      --danger: #f08a78;
      --composer-fade: rgba(38,38,37,0);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .app {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr);
    }
    aside {
      border-right: 1px solid var(--line);
      background: color-mix(in srgb, var(--panel) 76%, transparent);
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .brand {
      font-weight: 680;
      padding: 4px 2px 8px;
    }
    .sidebar-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .theme-toggle {
      width: 36px;
      min-width: 36px;
      padding: 0;
      margin: 0;
      background: var(--control);
      color: var(--text);
      border-color: var(--line);
    }
    .history {
      display: flex;
      flex-direction: column;
      gap: 6px;
      overflow: auto;
    }
    .history-item, .new-chat {
      width: 100%;
      margin: 0;
      text-align: left;
      justify-content: flex-start;
      color: var(--text);
      background: transparent;
      border-color: transparent;
      height: auto;
      min-height: 36px;
      padding: 8px 10px;
    }
    .new-chat {
      border-color: var(--line);
      background: var(--control);
      text-align: center;
      justify-content: center;
    }
    .history-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 34px;
      gap: 4px;
      align-items: center;
    }
    .history-item.active, .history-item:hover, .history-delete:hover {
      background: var(--hover);
      border-color: var(--line);
    }
    .history-delete {
      min-width: 34px;
      width: 34px;
      margin: 0;
      padding: 0;
      background: transparent;
      color: var(--muted);
      border-color: transparent;
      text-align: center;
    }
    .history-delete:hover { color: var(--danger); }
    .history-delete:disabled {
      opacity: 0.35;
      cursor: not-allowed;
    }
    .history-title {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .history-meta {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }
    .chat-shell {
      min-width: 0;
      display: flex;
      flex-direction: column;
    }
    header {
      height: 58px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-bottom: 1px solid var(--line);
      background: color-mix(in srgb, var(--bg) 88%, transparent);
      backdrop-filter: blur(14px);
      position: sticky;
      top: 0;
      z-index: 2;
    }
    h1 { margin: 0; font-size: 16px; font-weight: 650; letter-spacing: 0; }
    main {
      width: min(860px, calc(100vw - 28px));
      min-height: calc(100vh - 58px);
      margin: 0 auto;
      display: flex;
      flex-direction: column;
    }
    #messages {
      flex: 1;
      padding: 42px 0 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .empty {
      margin: auto;
      text-align: center;
      color: var(--muted);
      max-width: 520px;
    }
    .empty strong {
      display: block;
      color: var(--text);
      font-size: 24px;
      line-height: 1.2;
      margin-bottom: 8px;
    }
    .message {
      max-width: 78%;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 14px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      box-shadow: none;
    }
    .message.user {
      align-self: flex-end;
      background: var(--user);
      border-color: var(--line);
    }
    .message.assistant {
      align-self: flex-start;
      background: var(--assistant);
    }
    .message-wrap {
      display: flex;
      flex-direction: column;
      gap: 5px;
      max-width: 78%;
    }
    .message-wrap.user { align-self: flex-end; }
    .message-wrap.assistant { align-self: flex-start; }
    .message-wrap .message { max-width: 100%; }
    .message-actions {
      display: flex;
      gap: 6px;
      opacity: 0;
      transition: opacity 0.15s ease;
    }
    .message-wrap:hover .message-actions { opacity: 1; }
    .message-actions button {
      margin: 0;
      height: 28px;
      border-radius: 8px;
      padding: 0 9px;
      background: var(--control);
      color: var(--muted);
      border-color: var(--line);
      font-size: 12px;
      font-weight: 560;
    }
    .message-actions button:hover {
      color: var(--text);
      border-color: var(--line);
    }
    .message :first-child { margin-top: 0; }
    .message :last-child { margin-bottom: 0; }
    .message p { margin: 0 0 10px; }
    .message pre {
      margin: 10px 0;
      padding: 10px 12px;
      border-radius: 10px;
      background: color-mix(in srgb, var(--bg) 82%, #000 18%);
      border: 1px solid var(--line);
      overflow-x: auto;
      white-space: pre;
    }
    .message code {
      border-radius: 6px;
      padding: 1px 5px;
      background: color-mix(in srgb, var(--bg) 78%, #000 10%);
      font: 0.92em ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    .message pre code {
      padding: 0;
      background: transparent;
    }
    .message ul, .message ol {
      margin: 8px 0 10px;
      padding-left: 22px;
    }
    .message blockquote {
      margin: 8px 0;
      padding-left: 12px;
      border-left: 3px solid var(--line);
      color: var(--muted);
    }
    .message.thinking {
      color: var(--muted);
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .thinking-dots {
      display: inline-flex;
      gap: 3px;
    }
    .thinking-dots span {
      width: 5px;
      height: 5px;
      border-radius: 999px;
      background: var(--muted);
      opacity: 0.35;
      animation: pulse 1.2s infinite ease-in-out;
    }
    .thinking-dots span:nth-child(2) { animation-delay: 0.16s; }
    .thinking-dots span:nth-child(3) { animation-delay: 0.32s; }
    @keyframes pulse {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.32; }
      40% { transform: translateY(-3px); opacity: 0.9; }
    }
    .composer {
      position: sticky;
      bottom: 0;
      padding: 12px 0 18px;
      background: linear-gradient(180deg, var(--composer-fade), var(--bg) 28%);
    }
    .box {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: none;
      padding: 10px;
    }
    textarea {
      width: 100%;
      min-height: 56px;
      max-height: 180px;
      resize: vertical;
      border: 0;
      outline: none;
      background: transparent;
      color: var(--text);
      padding: 6px 8px;
      font: inherit;
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 10px;
      padding-top: 8px;
      border-top: 1px solid var(--line);
    }
    select, input, button {
      height: 36px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: var(--control);
      color: var(--text);
      padding: 0 10px;
      font: inherit;
    }
    select { min-width: 190px; max-width: 42vw; }
    input { width: 86px; }
    button {
      margin-left: auto;
      background: var(--accent);
      color: var(--bg);
      border-color: var(--accent);
      cursor: pointer;
      font-weight: 620;
      padding: 0 16px;
    }
    button:disabled { opacity: 0.48; cursor: not-allowed; }
    .status {
      color: var(--muted);
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .quick-start {
      display: flex;
      gap: 8px;
      justify-content: center;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    .quick-start button {
      margin: 0;
      background: var(--control);
      color: var(--text);
      border-color: var(--line);
    }
    @media (max-width: 640px) {
      .app { display: block; }
      aside {
        position: sticky;
        top: 0;
        z-index: 4;
        border-right: 0;
        border-bottom: 1px solid var(--line);
        padding: 10px;
      }
      .brand { display: none; }
      .history {
        flex-direction: row;
        overflow-x: auto;
        padding-bottom: 2px;
      }
      .history-row {
        width: 150px;
        flex: 0 0 150px;
      }
      .history-item { min-width: 0; }
      .new-chat {
        min-width: 104px;
        width: auto;
      }
      header { height: 50px; }
      main { width: min(100vw - 18px, 860px); }
      #messages { padding-top: 22px; gap: 12px; }
      .message, .message-wrap { max-width: 94%; }
      .controls { flex-wrap: wrap; }
      select { min-width: 0; max-width: 100%; flex: 1 1 100%; }
      input { width: 74px; }
      .status { flex: 1 1 auto; min-width: 0; }
      button { margin-left: 0; flex: 1; }
      .composer { padding-bottom: max(12px, env(safe-area-inset-bottom)); }
      .box { border-radius: 14px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="sidebar-top">
        <div class="brand">LightWeight</div>
        <button class="theme-toggle" id="themeToggle" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">☾</button>
      </div>
      <button class="new-chat" id="newChat" type="button">New chat</button>
      <div class="history" id="historyList"></div>
    </aside>
    <div class="chat-shell">
      <header><h1>LightWeight Chat</h1></header>
      <main>
        <section id="messages">
          <div class="empty" id="empty">
            <strong>Ask your local model</strong>
            <span>Choose a downloaded model and start chatting. If the list is empty, pull a model first.</span>
            <div class="quick-start" id="quickStart">
              <button type="button" data-command="lightweight pull qwen:7b --mode fit">Recommended pull</button>
              <button type="button" data-command="lightweight pull ggml-org/tiny-llamas --quant Q4_0 --mode extreme --run-anyway">Tiny test model</button>
            </div>
          </div>
        </section>
        <form class="composer" id="form">
          <div class="box">
            <textarea id="prompt" placeholder="Message LightWeight..." autocomplete="off"></textarea>
            <div class="controls">
              <select id="model"></select>
              <label class="status">Tokens <input id="tokens" type="number" min="1" max="8192" value="512" /></label>
              <span class="status" id="status">Loading models...</span>
              <button id="send" type="submit">Send</button>
            </div>
          </div>
        </form>
      </main>
    </div>
  </div>
  <script>
    const messagesEl = document.getElementById("messages");
    const emptyEl = document.getElementById("empty");
    const form = document.getElementById("form");
    const promptEl = document.getElementById("prompt");
    const modelEl = document.getElementById("model");
    const tokensEl = document.getElementById("tokens");
    const statusEl = document.getElementById("status");
    const sendEl = document.getElementById("send");
    const newChatEl = document.getElementById("newChat");
    const historyListEl = document.getElementById("historyList");
    const quickStartEl = document.getElementById("quickStart");
    const themeToggleEl = document.getElementById("themeToggle");
    const STORAGE_KEY = "lightweight.chat.sessions";
    const THEME_KEY = "lightweight.chat.theme";
    let abortController = null;
    let isGenerating = false;
    let activeId = "";
    let modelsById = {};
    let conversations = loadConversations();

    function setStatus(text) { statusEl.textContent = text; }

    function applyTheme(theme) {
      const next = theme === "dark" ? "dark" : "light";
      document.documentElement.dataset.theme = next;
      themeToggleEl.textContent = next === "dark" ? "☼" : "☾";
      themeToggleEl.title = next === "dark" ? "Switch to light mode" : "Switch to dark mode";
      localStorage.setItem(THEME_KEY, next);
    }

    function escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function inlineMarkdown(value) {
      return escapeHtml(value)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>")
        .replace(/\\*([^*]+)\\*/g, "<em>$1</em>");
    }

    function renderMarkdown(value) {
      const lines = String(value || "").replace(/\\r\\n/g, "\\n").split("\\n");
      const html = [];
      let paragraph = [];
      let list = null;
      let inCode = false;
      let code = [];

      function flushParagraph() {
        if (!paragraph.length) return;
        html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
        paragraph = [];
      }
      function flushList() {
        if (!list) return;
        html.push(`<${list.type}>${list.items.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</${list.type}>`);
        list = null;
      }

      for (const line of lines) {
        if (line.trim().startsWith("```")) {
          if (inCode) {
            html.push(`<pre><code>${escapeHtml(code.join("\\n"))}</code></pre>`);
            code = [];
            inCode = false;
          } else {
            flushParagraph();
            flushList();
            inCode = true;
          }
          continue;
        }
        if (inCode) {
          code.push(line);
          continue;
        }
        if (!line.trim()) {
          flushParagraph();
          flushList();
          continue;
        }
        const heading = line.match(/^(#{1,3})\\s+(.+)$/);
        if (heading) {
          flushParagraph();
          flushList();
          const level = heading[1].length + 2;
          html.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
          continue;
        }
        const bullet = line.match(/^\\s*[-*]\\s+(.+)$/);
        const ordered = line.match(/^\\s*\\d+\\.\\s+(.+)$/);
        if (bullet || ordered) {
          flushParagraph();
          const type = ordered ? "ol" : "ul";
          if (!list || list.type !== type) flushList();
          if (!list) list = { type, items: [] };
          list.items.push((bullet || ordered)[1]);
          continue;
        }
        const quote = line.match(/^>\\s?(.+)$/);
        if (quote) {
          flushParagraph();
          flushList();
          html.push(`<blockquote>${inlineMarkdown(quote[1])}</blockquote>`);
          continue;
        }
        paragraph.push(line.trim());
      }
      if (inCode) html.push(`<pre><code>${escapeHtml(code.join("\\n"))}</code></pre>`);
      flushParagraph();
      flushList();
      return html.join("") || escapeHtml(value);
    }

    function modelStatus(model) {
      if (!model) return "Model ready";
      if (!model.squeeze) return `${model.id} ready`;
      const parts = [
        model.squeeze.profile || "profile",
        model.squeeze.verdict || "planned",
        model.squeeze.active_set || "active-set",
        model.squeeze.verified ? "verified" : "not verified"
      ];
      return parts.join(" · ");
    }

    function newConversation() {
      return { id: String(Date.now()), title: "New chat", messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    }

    function loadConversations() {
      try {
        const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
        if (Array.isArray(parsed) && parsed.length) return parsed;
      } catch (_error) {}
      return [newConversation()];
    }

    function currentConversation() {
      let found = conversations.find((item) => item.id === activeId);
      if (!found) {
        found = conversations[0] || newConversation();
        activeId = found.id;
      }
      return found;
    }

    function persist() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, 40)));
      renderHistory();
    }

    function renderHistory() {
      historyListEl.innerHTML = "";
      for (const item of conversations) {
        const row = document.createElement("div");
        row.className = "history-row";
        const button = document.createElement("button");
        button.type = "button";
        button.className = item.id === activeId ? "history-item active" : "history-item";
        button.innerHTML = `<span class="history-title"></span><span class="history-meta">${item.messages.length} messages</span>`;
        button.querySelector(".history-title").textContent = item.title || "New chat";
        button.addEventListener("click", () => {
          if (isGenerating) return;
          activeId = item.id;
          renderHistory();
          renderMessages();
        });
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "history-delete";
        remove.textContent = "×";
        remove.title = "Delete chat";
        remove.disabled = conversations.length <= 1;
        remove.addEventListener("click", () => deleteConversation(item.id));
        row.appendChild(button);
        row.appendChild(remove);
        historyListEl.appendChild(row);
      }
    }

    function deleteConversation(id) {
      if (isGenerating || conversations.length <= 1) return;
      conversations = conversations.filter((item) => item.id !== id);
      if (activeId === id) activeId = conversations[0]?.id || "";
      persist();
      renderMessages();
    }

    function renderMessages() {
      const conversation = currentConversation();
      messagesEl.innerHTML = "";
      if (!conversation.messages.length) {
        messagesEl.appendChild(emptyEl);
        emptyEl.style.display = "block";
        return;
      }
      emptyEl.style.display = "none";
      for (let i = 0; i < conversation.messages.length; i += 1) {
        addMessage(conversation.messages[i].role, conversation.messages[i].content, i);
      }
    }

    function addMessage(role, content, index = null) {
      emptyEl.style.display = "none";
      const wrap = document.createElement("div");
      wrap.className = `message-wrap ${role}`;
      const el = document.createElement("div");
      el.className = `message ${role}`;
      if (role === "assistant") {
        el.innerHTML = renderMarkdown(content);
      } else {
        el.textContent = content;
      }
      wrap.appendChild(el);
      if (role === "assistant" && index !== null) {
        const actions = document.createElement("div");
        actions.className = "message-actions";
        actions.innerHTML = '<button type="button" data-action="copy">Copy</button><button type="button" data-action="regenerate">Regenerate</button><button type="button" data-action="delete">Delete</button>';
        actions.addEventListener("click", (event) => {
          const action = event.target?.dataset?.action;
          if (!action) return;
          if (action === "copy") navigator.clipboard.writeText(content);
          if (action === "delete") {
            currentConversation().messages.splice(index, 1);
            persist();
            renderMessages();
          }
          if (action === "regenerate") regenerateFrom(index);
        });
        wrap.appendChild(actions);
      }
      messagesEl.appendChild(wrap);
      wrap.scrollIntoView({ behavior: "smooth", block: "end" });
      return el;
    }

    function addThinkingMessage() {
      emptyEl.style.display = "none";
      const el = document.createElement("div");
      el.className = "message assistant thinking";
      el.innerHTML = '<span>Thinking</span><span class="thinking-dots"><span></span><span></span><span></span></span>';
      messagesEl.appendChild(el);
      el.scrollIntoView({ behavior: "smooth", block: "end" });
      return el;
    }

    function startNewChat() {
      const chat = newConversation();
      conversations.unshift(chat);
      activeId = chat.id;
      persist();
      renderMessages();
      promptEl.focus();
    }

    function updateTitle(conversation) {
      const firstUser = conversation.messages.find((item) => item.role === "user");
      conversation.title = firstUser ? firstUser.content.slice(0, 42) : "New chat";
      conversation.updatedAt = Date.now();
      conversations = [conversation, ...conversations.filter((item) => item.id !== conversation.id)];
    }

    function setGenerating(value) {
      isGenerating = value;
      sendEl.textContent = value ? "Stop" : "Send";
      modelEl.disabled = value;
      tokensEl.disabled = value;
    }

    function regenerateFrom(index) {
      if (isGenerating) return;
      const conversation = currentConversation();
      conversation.messages = conversation.messages.slice(0, index);
      persist();
      renderMessages();
      submitPrompt(null, true);
    }

    async function loadModels() {
      try {
        const res = await fetch("/v1/models");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = await res.json();
        modelEl.innerHTML = "";
        modelsById = {};
        for (const model of payload.data || []) {
          modelsById[model.id] = model;
          const option = document.createElement("option");
          option.value = model.id;
          option.textContent = model.squeeze
            ? `${model.id} · ${model.squeeze.profile} · ${model.squeeze.verdict}`
            : model.id;
          modelEl.appendChild(option);
        }
        if (!modelEl.options.length) {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "No local models";
          modelEl.appendChild(option);
          sendEl.disabled = true;
          setStatus("Pull a model first");
          promptEl.placeholder = "Copy a pull command from the quick start buttons first...";
        } else {
          sendEl.disabled = false;
          setStatus(modelStatus(modelsById[modelEl.value]) || `${modelEl.options.length} model(s) ready`);
          promptEl.placeholder = "Message LightWeight...";
        }
      } catch (error) {
        sendEl.disabled = true;
        setStatus(`Models unavailable: ${error.message}`);
      }
    }

    modelEl.addEventListener("change", () => {
      setStatus(modelStatus(modelsById[modelEl.value]));
    });

    async function submitPrompt(event, regenerate = false) {
      if (event) event.preventDefault();
      if (isGenerating) {
        abortController?.abort();
        setStatus("Stopping...");
        return;
      }
      const text = promptEl.value.trim();
      const model = modelEl.value;
      const conversation = currentConversation();
      if ((!text && !regenerate) || !model) return;

      promptEl.value = "";
      if (!regenerate) {
        conversation.messages.push({ role: "user", content: text });
      }
      updateTitle(conversation);
      persist();
      renderMessages();
      const assistantEl = addThinkingMessage();
      abortController = new AbortController();
      setGenerating(true);
      setStatus("Thinking...");
      const started = performance.now();
      let firstToken = true;

      try {
        const res = await fetch("/v1/chat/completions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              model,
              messages: conversation.messages,
              max_tokens: Number(tokensEl.value || 512),
              stream: true
            }),
            signal: abortController.signal
          });
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}));
          throw new Error(payload.detail || payload.error || `HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let reply = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\\n\\n");
          buffer = events.pop() || "";

          for (const event of events) {
            const line = event.split("\\n").find((item) => item.startsWith("data: "));
            if (!line) continue;
            const data = line.slice(6).trim();
            if (data === "[DONE]") continue;
            const payload = JSON.parse(data);
            if (payload.error) throw new Error(payload.error);
            const delta = payload.choices?.[0]?.delta?.content || "";
            if (delta) {
              if (firstToken) {
                firstToken = false;
                const elapsed = ((performance.now() - started) / 1000).toFixed(1);
                assistantEl.classList.remove("thinking");
                assistantEl.textContent = "";
                setStatus(`Writing... thought for ${elapsed}s`);
              }
                reply += delta;
              assistantEl.innerHTML = renderMarkdown(reply);
              assistantEl.scrollIntoView({ behavior: "smooth", block: "end" });
            }
          }
        }

        assistantEl.classList.remove("thinking");
        assistantEl.innerHTML = reply ? renderMarkdown(reply) : "(empty response)";
        conversation.messages.push({ role: "assistant", content: reply });
        updateTitle(conversation);
        persist();
        renderMessages();
        setStatus("Ready");
      } catch (error) {
        assistantEl.classList.remove("thinking");
        if (error.name === "AbortError") {
          assistantEl.textContent = "Stopped.";
          setStatus("Stopped");
        } else {
          assistantEl.textContent = `Error: ${error.message}`;
          setStatus("Request failed");
        }
      } finally {
        abortController = null;
        setGenerating(false);
        promptEl.focus();
      }
    }

    form.addEventListener("submit", submitPrompt);

    promptEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    themeToggleEl.addEventListener("click", () => {
      applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    });

    newChatEl.addEventListener("click", startNewChat);
    quickStartEl.addEventListener("click", (event) => {
      const command = event.target?.dataset?.command;
      if (!command) return;
      navigator.clipboard.writeText(command);
      setStatus("Pull command copied");
    });

    applyTheme(localStorage.getItem(THEME_KEY) || "light");
    activeId = conversations[0].id;
    renderHistory();
    renderMessages();
    loadModels();
  </script>
</body>
</html>
"""

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message content must not be empty")
        return value

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage] = Field(min_length=1)
    lora: Optional[str] = None
    stream: bool = False
    max_tokens: int = Field(default=512, ge=1, le=8192)

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(_load_chat_html())

@app.get("/v1/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "thermal": os.environ.get("LIGHTWEIGHT_THERMAL", "balanced"),
    }

@app.get("/v1/models")
async def models():
    manager = ModelManager()
    models_data = []
    for model in manager.list_local_models():
        squeeze = manager.get_squeeze_profile(model["name"])
        models_data.append({
            "id": model["name"],
            "object": "model",
            "owned_by": "local",
            "size_mb": model.get("size", 0),
            "repo": model.get("repo"),
            "quant": model.get("quant"),
            "active_squeeze_profile": model.get("active_squeeze_profile"),
            "squeeze": {
                "profile": squeeze.get("profile"),
                "verdict": squeeze.get("verdict"),
                "active_set": squeeze.get("active_set"),
                "ctx": squeeze.get("ctx"),
                "verified": bool(squeeze.get("verification", {}).get("ok")),
            } if squeeze else None,
        })
    return {
        "object": "list",
        "data": models_data,
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    model_name = request.model
    async with inference_lock:
        model_name = request.model
        manager = ModelManager()
        model_path = manager.get_model_path(model_name)
        if not model_path:
            for m in manager.list_local_models():
                if model_name.lower() in m["name"].lower():
                    model_path, model_name = m["path"], m["name"]; break

        if not model_path:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

        cache_key = model_name
        if request.lora:
            cache_key = f"{model_name}|lora={request.lora}"
        engine = engine_cache.get(cache_key)
        
        if not engine:
            detector = Detector(); report = detector.get_report()
            model_size = os.path.getsize(model_path) // (1024 * 1024)
            metadata = read_model_metadata(model_path)
            thermal = os.environ.get("LIGHTWEIGHT_THERMAL", "balanced")
            strategy = StrategyEngine(report).determine_strategy(
                model_size,
                model_name=model_name,
                thermal_mode=thermal,
            )
            strategy = _apply_squeeze_profile(strategy, manager.get_squeeze_profile(model_name))
            strategy = apply_metadata(strategy, metadata)
            strategy = _apply_runtime_profile(strategy, manager.get_runtime_profile(model_name, thermal))
            
            engine = InferenceEngine(model_path, strategy)
            engine.load(lora_path=request.lora) # Fixed Signature!
            engine_cache.put(cache_key, engine)

    messages = [message.model_dump() for message in request.messages]
    prompt = messages[-1]["content"]

    if request.stream:
        async def event_generator():
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[dict | None] = asyncio.Queue()

            def run_generation():
                try:
                    with engine.generation_lock:
                        for chunk in engine.generate(prompt, max_tokens=request.max_tokens, messages=messages):
                            loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, {"error": str(exc)})
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            threading.Thread(target=run_generation, daemon=True).start()

            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                if "error" in chunk:
                    yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                    break
                else:
                    data = {
                        "choices": [{"delta": {"content": chunk["text"]}, "index": 0, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    def run_full_generation():
        with engine.generation_lock:
            return list(engine.generate(prompt, max_tokens=request.max_tokens, messages=messages))

    chunks = await asyncio.to_thread(run_full_generation)
    full_text = "".join(chunk["text"] for chunk in chunks)
                
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "model": model_name,
        "choices": [{"message": {"role": "assistant", "content": full_text}, "index": 0, "finish_reason": "stop"}]
    }
