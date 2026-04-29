#!/usr/bin/env python3
"""Local web UI for agentic-coding-notify preferences.

Run:
  python3 web/notify_ui.py

Then open http://127.0.0.1:8765.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get("AGENTIC_CODING_NOTIFY_CONFIG", Path.home() / ".agentic-coding-notify" / "config.json"))
SYSTEM_SOUND_DIR = Path("/System/Library/Sounds")
SAMPLE_PROCESSES: dict[str, subprocess.Popen] = {}

DEFAULT_CONFIG = {
    "voice": "Zarvox",
    "rate": "250",
    "notification_sound": "Submarine",
    "start_sound": "Basso",
    "end_sound": "Submarine",
    "app_voice_text_template": "{service} App",
    "cli_voice_text_template": "{service} {label}",
    "voice_text_template": "",
}

HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>agentic-coding-notify</title>
  <style>
    :root {
      color-scheme: light;
      --font-ui: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
      --font-display: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
      --font-mono: "JetBrains Mono", "SFMono-Regular", ui-monospace, Menlo, Consolas, monospace;
      --n64-gray: #c9c5bb;
      --n64-gray-dark: #6d6962;
      --n64-gray-line: #a9a49a;
      --n64-cream: #f4f1e8;
      --n64-offwhite: #fbf8ef;
      --n64-blue: #2f68d8;
      --n64-green: #2faf65;
      --n64-yellow: #f1bf28;
      --n64-red: #dd3f46;
      --n64-ink: #24211d;
      --text: var(--n64-ink);
      --muted: #5f5a52;
      --faint: #817b72;
      --line: rgba(104, 99, 91, .24);
      --line-strong: rgba(104, 99, 91, .38);
      --accent: var(--n64-blue);
      --accent-2: var(--n64-green);
      --warn: var(--n64-yellow);
      --danger: var(--n64-red);
      --shadow: 0 18px 0 rgba(109,105,98,.18), 0 30px 64px rgba(74, 70, 63, .18);
      font-family: var(--font-ui);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 12% 4%, rgba(47, 104, 216, .14), transparent 29%),
        radial-gradient(circle at 90% 8%, rgba(47, 175, 101, .13), transparent 26%),
        radial-gradient(circle at 82% 84%, rgba(221, 63, 70, .10), transparent 30%),
        linear-gradient(145deg, #d1cdc3 0%, var(--n64-cream) 40%, #bdb8ad 100%);
      color: var(--text);
      font-family: var(--font-ui);
      letter-spacing: -.01em;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .28;
      background-image:
        linear-gradient(rgba(64, 59, 52, .16) 1px, transparent 1px),
        linear-gradient(90deg, rgba(64, 59, 52, .13) 1px, transparent 1px);
      background-size: 34px 34px;
      mask-image: radial-gradient(circle at top, #000 0%, transparent 74%);
    }
    main { position: relative; max-width: 1120px; margin: 0 auto; padding: 34px 22px 56px; }
    .hero { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 18px; align-items: end; margin-bottom: 22px; }
    .eyebrow { margin: 0 0 8px; color: var(--n64-red); font-size: 12px; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; }
    h1 { margin: 0; font-family: var(--font-display); font-size: clamp(34px, 6vw, 58px); line-height: .92; letter-spacing: -.065em; color: #28251f; text-shadow: 2px 2px 0 rgba(255, 255, 255, .72), 4px 4px 0 rgba(47, 104, 216, .18); }
    .subtitle { max-width: 660px; margin: 14px 0 0; color: var(--muted); font-size: 15px; line-height: 1.6; }
    .status-pill { justify-self: end; min-width: 220px; border: 1px solid var(--line-strong); border-radius: 20px; background: linear-gradient(180deg, rgba(251, 248, 239, .92), rgba(201, 197, 187, .76)); padding: 14px 15px; box-shadow: inset 0 1px 0 rgba(255,255,255,.78), 0 18px 42px rgba(74,70,63,.16); }
    .status-pill span { display: block; color: var(--faint); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; }
    .status-pill strong { display: block; margin-top: 5px; color: var(--n64-green); font-family: var(--font-mono); font-size: 13px; font-weight: 900; font-variant-numeric: tabular-nums; }
    .palette-strip { display: flex; gap: 6px; margin-top: 12px; }
    .swatch { width: 23px; height: 8px; border-radius: 999px; border: 1px solid rgba(36,33,29,.16); }
    .swatch.gray { background: var(--n64-gray-dark); }
    .swatch.blue { background: var(--n64-blue); }
    .swatch.green { background: var(--n64-green); }
    .swatch.yellow { background: var(--n64-yellow); }
    .swatch.red { background: var(--n64-red); }
    .grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-items: start; }
    .card {
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(180deg, rgba(255, 252, 244, .94), rgba(234, 230, 220, .92)) padding-box,
        linear-gradient(135deg, rgba(109,105,98,.72), rgba(255,255,255,.68), rgba(47,104,216,.26), rgba(221,63,70,.16)) border-box;
      border: 1px solid transparent;
      border-radius: 22px;
      padding: 20px;
      box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,.78), inset 0 -1px 0 rgba(109,105,98,.16);
      backdrop-filter: blur(18px);
    }
    .card::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 5px; background: linear-gradient(90deg, var(--n64-gray-dark), var(--n64-blue), var(--n64-green), var(--n64-yellow), var(--n64-red)); opacity: .72; }
    .card::after { content: ""; position: absolute; inset: 0; pointer-events: none; border-radius: inherit; box-shadow: inset 0 0 0 1px rgba(255,255,255,.22); }
    .full { grid-column: 1 / -1; }
    h2 { display: flex; align-items: center; gap: 10px; margin: 0 0 12px; font-size: 16px; letter-spacing: -.025em; color: #302c26; }
    .section-index, .mono, code, pre, #rateLabel, #spokenPreview, #configPath { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
    .section-index { color: var(--n64-red); font-size: 12px; letter-spacing: .08em; }
    p { color: var(--muted); line-height: 1.5; }
    label { display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 12px; color: #4f4941; margin: 14px 0 7px; letter-spacing: .01em; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line-strong);
      background: rgba(255, 253, 247, .86);
      color: var(--text);
      border-radius: 14px;
      padding: 11px 12px;
      font: inherit;
      outline: none;
      transition: border-color .14s ease, box-shadow .14s ease, background .14s ease;
    }
    input:focus, select:focus, textarea:focus { border-color: rgba(47, 104, 216, .64); box-shadow: 0 0 0 3px rgba(47, 104, 216, .13), 0 0 18px rgba(241, 191, 40, .18); background: #fffdf7; }
    input[list] { padding-right: 34px; background-image: linear-gradient(45deg, transparent 50%, var(--n64-gray-dark) 50%), linear-gradient(135deg, var(--n64-gray-dark) 50%, transparent 50%); background-position: calc(100% - 18px) 18px, calc(100% - 12px) 18px; background-size: 6px 6px, 6px 6px; background-repeat: no-repeat; }
    textarea { min-height: 92px; resize: vertical; }
    input[type="range"] { padding: 0; accent-color: var(--n64-blue); }
    .row { display: flex; gap: 10px; align-items: start; }
    .row > * { flex: 1; min-width: 0; }
    .sound-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 9px; align-items: center; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
    button {
      border: 1px solid rgba(36, 33, 29, .16);
      border-radius: 999px;
      padding: 10px 15px;
      background: linear-gradient(180deg, #ffe06c, var(--n64-yellow));
      color: #1d1707;
      font-weight: 900;
      cursor: pointer;
      letter-spacing: -.015em;
      box-shadow: 0 10px 22px rgba(74,70,63,.18), inset 0 1px 0 rgba(255,255,255,.62);
    }
    button:hover { transform: translateY(-1px); }
    button.secondary { background: linear-gradient(180deg, rgba(255,255,255,.62), rgba(201,197,187,.42)); color: var(--text); border: 1px solid var(--line-strong); box-shadow: inset 0 1px 0 rgba(255,255,255,.72); }
    button.warn { background: linear-gradient(180deg, #5edb90, var(--n64-green)); color: #06140d; }
    .icon-button { width: 43px; height: 43px; padding: 0; display: inline-grid; place-items: center; border: 1px solid var(--line-strong); border-radius: 14px; background: rgba(255, 253, 247, .88); color: var(--n64-blue); box-shadow: inset 0 0 0 1px rgba(255,255,255,.46); }
    .icon-button:hover { background: #fffdf7; color: #174fc1; }
    .icon-button svg { width: 18px; height: 18px; stroke: currentColor; stroke-width: 2; fill: none; stroke-linecap: round; stroke-linejoin: round; }
    .icon-button.play svg { fill: currentColor; stroke: currentColor; }
    .icon-button .stop-icon { display: none; }
    .icon-button.is-playing { background: rgba(221, 63, 70, .11); color: var(--n64-red); border-color: rgba(221, 63, 70, .42); }
    .icon-button.is-playing .play-icon { display: none; }
    .icon-button.is-playing .stop-icon { display: block; }
    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
    .preview { margin-top: 14px; border: 1px solid var(--line-strong); border-radius: 18px; padding: 14px; background: rgba(255, 253, 247, .62); }
    .preview strong { display: block; margin-bottom: 6px; color: #312d27; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; }
    .hint { margin: 7px 0 0; font-size: 12px; color: var(--faint); }
    .notice { border-color: rgba(47, 175, 101, .30); background: linear-gradient(180deg, rgba(47,175,101,.11), rgba(255,252,244,.88)); }
    .notice p { margin: 0; color: #365344; }
    .chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 13px; }
    .chip { border: 1px solid var(--line-strong); border-radius: 999px; padding: 6px 9px; color: var(--muted); background: rgba(255,255,255,.56); font-size: 12px; }
    .chip.palette-note { border-color: rgba(109,105,98,.48); color: #4f4941; }
    pre { white-space: pre-wrap; background: rgba(255,253,247,.72); border: 1px solid var(--line-strong); border-radius: 16px; padding: 14px; min-height: 118px; max-height: 360px; overflow: auto; color: #3b3630; font-size: 12px; }
    @media (max-width: 820px) {
      main { padding: 24px 14px 40px; }
      .hero, .grid { grid-template-columns: 1fr; }
      .status-pill { justify-self: stretch; }
      .full { grid-column: auto; }
      .row { flex-direction: column; }
    }
  </style>
</head>
<body>
<main>
  <header class="hero">
    <div>
      <p class="eyebrow">local macOS control panel</p>
      <h1>agentic-coding-notify</h1>
      <p class="subtitle">Local notification preferences for agent apps and CLIs: voice, speech rate, sounds, spoken templates, and test runs.</p>
    </div>
    <div class="status-pill" aria-label="Local UI endpoint">
      <span>local UI</span>
      <strong>127.0.0.1:8765</strong>
      <div class="palette-strip" aria-label="N64 gray palette">
        <i class="swatch gray"></i>
        <i class="swatch blue"></i>
        <i class="swatch green"></i>
        <i class="swatch yellow"></i>
        <i class="swatch red"></i>
      </div>
    </div>
  </header>

  <div class="grid">
    <section class="card">
      <h2><span class="section-index">01</span>Voice</h2>
      <label for="voice">Voice</label>
      <div class="sound-row">
        <input id="voice" list="voice_options" autocomplete="off" placeholder="Type to filter voices" />
        <datalist id="voice_options"></datalist>
        <button id="voice_toggle" class="icon-button play" title="Play voice sample" aria-label="Play voice sample" onclick="toggleVoice()">
          <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
          <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
          <span class="sr-only">Play</span>
        </button>
      </div>
      <p class="hint">Voice samples say <code>Agentic Coding Notify</code>.</p>

      <label for="rate">Speech rate <span id="rateLabel"></span></label>
      <input id="rate" type="range" min="80" max="420" step="5" />
      <p class="hint">macOS <code>say -r</code> uses words per minute. <code>250</code> is roughly <code>1.25x</code> a <code>200</code> wpm baseline.</p>
    </section>

    <section class="card">
      <h2><span class="section-index">02</span>Sounds</h2>
      <label for="notification_sound">Notification sound</label>
      <div class="sound-row">
        <input id="notification_sound" list="sound_options" autocomplete="off" placeholder="Type to filter sounds" />
        <datalist id="sound_options"></datalist>
        <button id="notification_sound_toggle" class="icon-button play" title="Play notification sample" aria-label="Play notification sample" onclick="toggleSound('notification_sound')">
          <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
          <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
          <span class="sr-only">Play</span>
        </button>
      </div>

      <div class="row">
        <div>
          <label for="start_sound">Start sound</label>
          <div class="sound-row">
            <input id="start_sound" list="sound_options" autocomplete="off" placeholder="Type to filter sounds" />
            <button id="start_sound_toggle" class="icon-button play" title="Play start sample" aria-label="Play start sample" onclick="toggleSound('start_sound')">
              <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
              <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
              <span class="sr-only">Play</span>
            </button>
          </div>
        </div>
        <div>
          <label for="end_sound">End sound</label>
          <div class="sound-row">
            <input id="end_sound" list="sound_options" autocomplete="off" placeholder="Type to filter sounds" />
            <button id="end_sound_toggle" class="icon-button play" title="Play end sample" aria-label="Play end sample" onclick="toggleSound('end_sound')">
              <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
              <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
              <span class="sr-only">Play</span>
            </button>
          </div>
        </div>
      </div>
      <div class="actions">
        <button class="secondary" onclick="applyClassicPreset()">Classic preset</button>
        <button class="secondary" onclick="stopAllSounds()">Stop all samples</button>
      </div>
    </section>

    <section class="card">
      <h2><span class="section-index">03</span>Text</h2>
      <label for="app_voice_text_template">App template</label>
      <input id="app_voice_text_template" />
      <p class="hint">Default classic style: <code>{service} App</code> → Claude App / Codex App.</p>

      <label for="cli_voice_text_template">CLI template</label>
      <input id="cli_voice_text_template" />
      <p class="hint">Default classic style: <code>{service} {label}</code> → Codex review / Claude api.</p>

      <label for="voice_text_template">Override spoken text</label>
      <input id="voice_text_template" placeholder="Leave blank to use app/CLI templates" />
      <p class="hint">Placeholders: <code>{service}</code>, <code>{label}</code>, <code>{voice_label}</code>, <code>{message}</code>, <code>{context}</code>.</p>
    </section>

    <section class="card notice">
      <h2><span class="section-index">04</span>Disclosure</h2>
      <p>Apps do not need terminal labels. CLI sessions can use short tab labels like <code>One</code>, <code>Two</code>, or <code>Three</code>; the plugin already detects the service.</p>
      <div class="chips" aria-label="Supported contexts">
        <span class="chip">Claude App</span>
        <span class="chip">Codex App</span>
        <span class="chip">Agent CLIs</span>
        <span class="chip palette-note">N64 gray palette</span>
      </div>
    </section>

    <section class="card full">
      <h2><span class="section-index">05</span>Preview</h2>
      <div class="grid">
        <div>
          <label for="service">Service</label>
          <input id="service" list="service_options" autocomplete="off" value="Claude App" placeholder="Type to filter services" />
          <datalist id="service_options"></datalist>
        </div>
        <div>
          <label for="label">CLI tab/profile label</label>
          <input id="label" value="review" />
          <p class="hint">Tip: in terminal, rename tabs to simple labels like <code>One</code>, <code>Two</code>, or <code>Three</code>. The plugin already detects the CLI service; the tab name just helps you track which session called.</p>
        </div>
      </div>
      <label for="message">Notification message</label>
      <textarea id="message">Teste do agentic-coding-notify</textarea>
      <div class="preview">
        <strong>Will say</strong>
        <code id="spokenPreview"></code>
        <p class="hint" id="soundPreview"></p>
      </div>
      <div class="actions">
        <button onclick="saveConfig()">Save config</button>
        <button class="secondary" onclick="testNotify(true)">Dry-run JSON</button>
        <button class="warn" onclick="testNotify(false)">Real notification</button>
      </div>
    </section>

    <section class="card full">
      <h2><span class="section-index">06</span>Status</h2>
      <p class="hint">Config path: <code id="configPath"></code></p>
      <pre id="status">Loading…</pre>
    </section>
  </div>
</main>
<script>
const fields = ["voice", "rate", "notification_sound", "start_sound", "end_sound", "app_voice_text_template", "cli_voice_text_template", "voice_text_template"];
const soundFields = ["notification_sound", "start_sound", "end_sound"];
const serviceOptions = ["Claude App", "Codex App", "Claude CLI", "Codex CLI", "OpenCode CLI", "Pi CLI"];
const voiceSampleText = "Agentic Coding Notify";
let options = { voices: [], sounds: [] };
let isLoading = true;
let sampleState = {};
let sampleTimers = {};
const classicPreset = {
  voice: "Zarvox",
  rate: "250",
  notification_sound: "Submarine",
  start_sound: "Basso",
  end_sound: "Submarine",
  app_voice_text_template: "{service} App",
  cli_voice_text_template: "{service} {label}",
  voice_text_template: ""
};

function $(id) { return document.getElementById(id); }
function status(value) { $("status").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2); }
function currentConfig() {
  const cfg = {};
  for (const f of fields) cfg[f] = $(f).value;
  return cfg;
}
function fillDatalist(id, values) {
  const el = $(id);
  el.innerHTML = "";
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    el.appendChild(option);
  }
}
function setConfig(cfg) {
  isLoading = true;
  for (const f of fields) if ($(f)) $(f).value = cfg[f] ?? "";
  updateRateLabel();
  updatePreview();
  isLoading = false;
}
function updateRateLabel() {
  const rate = Number($("rate").value || 250);
  $("rateLabel").textContent = `${rate} wpm (~${(rate / 200).toFixed(2)}x)`;
}
function selectedServiceParts() {
  const raw = $("service").value;
  const isApp = raw.endsWith(" App");
  return {
    raw,
    service: raw.replace(/ (App|CLI)$/, ""),
    label: isApp ? `${raw.replace(/ App$/, "")} App` : ($("label").value || raw.replace(/ CLI$/, "")),
    context: isApp ? "app" : "cli"
  };
}
function renderTemplate(template, values) {
  let output = template || "{voice_label}";
  for (const [key, value] of Object.entries(values)) {
    output = output.split(`{${key}}`).join(value);
  }
  return output.trim().replace(/\s+/g, " ");
}
function computeSpokenPreview() {
  const parts = selectedServiceParts();
  const fallback = parts.context === "app" ? parts.label : `${parts.service} ${parts.label}`;
  const template = $("voice_text_template").value || (parts.context === "app" ? $("app_voice_text_template").value : $("cli_voice_text_template").value);
  return renderTemplate(template, {
    service: parts.service,
    label: parts.label,
    context: parts.context,
    voice_label: fallback,
    message: $("message").value
  });
}
function updatePreview() {
  $("spokenPreview").textContent = computeSpokenPreview();
  $("soundPreview").textContent = `Voice: ${$("voice").value} @ ${$("rate").value} wpm · start: ${$("start_sound").value} · notification: ${$("notification_sound").value} · end: ${$("end_sound").value}`;
}
function applyClassicPreset() {
  setConfig(classicPreset);
  status({ preset: "classic", config: currentConfig() });
}
async function load() {
  options = await (await fetch("/api/options")).json();
  fillDatalist("voice_options", options.voices);
  fillDatalist("sound_options", ["none", ...options.sounds]);
  fillDatalist("service_options", serviceOptions);
  $("configPath").textContent = options.config_path;
  const cfg = await (await fetch("/api/config")).json();
  setConfig(cfg);
  status({ loaded: true, config: cfg });
}
async function saveConfig() {
  const res = await fetch("/api/config", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(currentConfig()) });
  status(await res.json());
}
async function testNotify(dryRun) {
  const body = { config: currentConfig(), service: $("service").value, label: $("label").value, message: $("message").value, dry_run: dryRun };
  const res = await fetch("/api/test", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  status(await res.json());
}
async function playSound(field) {
  const res = await fetch("/api/play-sound", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ field, sound: $(field).value }) });
  const payload = await res.json();
  status(payload);
  if (payload.ok) setSoundPlaying(field, true);
}
async function stopSound(field) {
  const res = await fetch("/api/stop-sound", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ field }) });
  const payload = await res.json();
  status(payload);
  setSoundPlaying(field, false);
}
async function stopAllSounds() {
  const res = await fetch("/api/stop-sound", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ field: "all" }) });
  const payload = await res.json();
  status(payload);
  for (const field of ["voice", ...soundFields]) setSoundPlaying(field, false);
}
async function playVoice() {
  const res = await fetch("/api/play-voice", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ field: "voice", voice: $("voice").value, rate: $("rate").value, text: voiceSampleText })
  });
  const payload = await res.json();
  status(payload);
  if (payload.ok) setSoundPlaying("voice", true);
}
async function stopVoice() {
  const res = await fetch("/api/stop-voice", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ field: "voice" }) });
  const payload = await res.json();
  status(payload);
  setSoundPlaying("voice", false);
}
async function toggleVoice() {
  if (sampleState.voice) {
    await stopVoice();
  } else {
    await playVoice();
  }
}
async function toggleSound(field) {
  if (sampleState[field]) {
    await stopSound(field);
  } else {
    await playSound(field);
  }
}
function setSoundPlaying(field, playing) {
  sampleState[field] = playing;
  if (sampleTimers[field]) {
    clearTimeout(sampleTimers[field]);
    sampleTimers[field] = null;
  }
  const button = $(`${field}_toggle`);
  if (!button) return;
  button.classList.toggle("is-playing", playing);
  const label = field === "voice" ? "voice" : field.replace("_sound", "").replace("_", " ");
  button.title = `${playing ? "Stop" : "Play"} ${label} sample`;
  button.setAttribute("aria-label", button.title);
  const text = button.querySelector(".sr-only");
  if (text) text.textContent = playing ? "Stop" : "Play";
  if (playing) {
    sampleTimers[field] = setTimeout(() => setSoundPlaying(field, false), 2500);
  }
}
for (const id of [...fields, "service", "label", "message"]) {
  document.addEventListener("input", (event) => {
    if (event.target && event.target.id === id) {
      if (id === "rate") updateRateLabel();
      updatePreview();
    }
  });
  document.addEventListener("change", (event) => {
    if (event.target && event.target.id === id) {
      updatePreview();
      if (!isLoading && id === "voice") playVoice();
      if (!isLoading && soundFields.includes(id)) playSound(id);
    }
  });
}
load().catch(err => status(String(err.stack || err)));
</script>
</body>
</html>
"""


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("content-length", "0") or 0)
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def write_json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    data = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("content-length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except Exception:
        data = {}
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: str(v) for k, v in data.items() if k in DEFAULT_CONFIG})
    return merged


def save_config(config: dict) -> dict:
    cleaned = dict(DEFAULT_CONFIG)
    for key in DEFAULT_CONFIG:
        if key in config:
            cleaned[key] = str(config[key])
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cleaned, indent=2) + "\n")
    return cleaned


def list_voices() -> list[str]:
    try:
        proc = subprocess.run(["/usr/bin/say", "-v", "?"], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:
        return ["Samantha", "Zarvox"]
    voices = []
    for line in proc.stdout.splitlines():
        match = re.match(r"^(.+?)\s{2,}\S+\s+#", line)
        if match:
            voices.append(match.group(1).strip())
    return sorted(set(voices), key=str.lower) or ["Samantha", "Zarvox"]


def list_sounds() -> list[str]:
    sounds = []
    if SYSTEM_SOUND_DIR.exists():
        sounds = sorted(path.stem for path in SYSTEM_SOUND_DIR.glob("*.aiff"))
    return sounds or ["Basso", "Submarine"]


def sound_to_path(sound: str) -> str | None:
    if not sound or sound.lower() == "none":
        return None
    candidate = Path(sound)
    if candidate.is_file():
        return str(candidate)
    name = sound[:-5] if sound.endswith(".aiff") else sound
    candidate = SYSTEM_SOUND_DIR / f"{name}.aiff"
    if candidate.is_file():
        return str(candidate)
    return None


def stop_sample(field: str) -> bool:
    proc = SAMPLE_PROCESSES.pop(field, None)
    if not proc:
        return False
    if proc.poll() is None:
        proc.terminate()
    return True


def stop_samples(field: str | None = None) -> list[str]:
    if field and field != "all":
        return [field] if stop_sample(field) else []
    stopped = []
    for key in list(SAMPLE_PROCESSES):
        if stop_sample(key):
            stopped.append(key)
    return stopped


def play_sample(field: str, sound: str) -> dict:
    path = sound_to_path(sound)
    if not path:
        return {"ok": False, "error": f"sound not found: {sound}"}
    stop_sample(field)
    SAMPLE_PROCESSES[field] = subprocess.Popen(["/usr/bin/afplay", path])
    return {"ok": True, "field": field, "sound": sound, "path": path}


def play_voice_sample(field: str, voice: str, rate: str, text: str) -> dict:
    cleaned_voice = voice.strip() or DEFAULT_CONFIG["voice"]
    cleaned_rate = rate.strip() or DEFAULT_CONFIG["rate"]
    cleaned_text = text.strip() or "Agentic Coding Notify"
    stop_sample(field)
    SAMPLE_PROCESSES[field] = subprocess.Popen(["/usr/bin/say", "-v", cleaned_voice, "-r", cleaned_rate, cleaned_text])
    return {"ok": True, "field": field, "voice": cleaned_voice, "rate": cleaned_rate, "text": cleaned_text}


def run_notify_test(body: dict) -> dict:
    config = body.get("config") or load_config()
    service = str(body.get("service") or "Codex App")
    label = str(body.get("label") or "review")
    message = str(body.get("message") or "Teste do agentic-coding-notify")
    dry_run = bool(body.get("dry_run", True))

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(config, tmp)
        tmp_path = tmp.name

    env = os.environ.copy()
    env["AGENTIC_CODING_NOTIFY_CONFIG"] = tmp_path
    if dry_run:
        env["NOTIFY_TEST_MODE"] = "1"

    try:
        if service == "Claude App":
            env["CLAUDE_CODE_ENTRYPOINT"] = "claude-desktop"
            cmd = ["bash", str(ROOT / "hooks/scripts/notify.sh")]
            input_data = json.dumps({"message": message, "title": "Claude Code"})
        elif service == "Claude CLI":
            env["TERM_PROGRAM"] = label
            cmd = ["bash", str(ROOT / "hooks/scripts/notify.sh")]
            input_data = json.dumps({"message": message, "title": "Claude Code"})
        elif service == "Codex App":
            env["CODEX_DESKTOP"] = "1"
            env["CODEX_NOTIFY_PARENT_PROCESS_TREE"] = "/usr/bin/zsh"
            env["CODEX_NOTIFY_COOLDOWN_FILE"] = str(Path(tempfile.gettempdir()) / "agentic-notify-ui-codex-cooldown.json")
            cmd = ["bash", str(ROOT / "adapters/codex/notify.sh"), json.dumps({"type": "agent-turn-complete", "cwd": f"/tmp/{label}", "last-assistant-message": message})]
            input_data = None
        elif service == "Codex CLI":
            env.pop("TERM_PROGRAM", None)
            env["CODEX_NOTIFY_PARENT_PROCESS_TREE"] = "/usr/bin/zsh"
            env["CODEX_NOTIFY_COOLDOWN_FILE"] = str(Path(tempfile.gettempdir()) / "agentic-notify-ui-codex-cooldown.json")
            cmd = ["bash", str(ROOT / "adapters/codex/notify.sh"), json.dumps({"type": "agent-turn-complete", "cwd": f"/tmp/{label}", "last-assistant-message": message})]
            input_data = None
        elif service == "OpenCode CLI":
            env["OPENCODE"] = "1"
            env["OPENCODE_NOTIFY_PARENT_PROCESS_TREE"] = "/usr/bin/zsh"
            env["OPENCODE_NOTIFY_COOLDOWN_FILE"] = str(Path(tempfile.gettempdir()) / "agentic-notify-ui-opencode-cooldown.json")
            cmd = ["bash", str(ROOT / "hooks/scripts/notify.sh"), json.dumps({"type": "agent-turn-complete", "cwd": f"/tmp/{label}", "message": f"READY_FOR_REVIEW: {message}"})]
            input_data = None
        elif service == "Pi CLI":
            env["PI_NOTIFY_PARENT_PROCESS_TREE"] = "/usr/bin/zsh"
            env["PI_NOTIFY_COOLDOWN_FILE"] = str(Path(tempfile.gettempdir()) / "agentic-notify-ui-pi-cooldown.json")
            cmd = ["bash", str(ROOT / "adapters/pi/notify.sh"), json.dumps({"type": "agent-turn-complete", "cwd": f"/tmp/{label}", "message": f"READY_FOR_REVIEW: {message}"})]
            input_data = None
        else:
            raise ValueError(f"Unknown service: {service}")

        proc = subprocess.run(cmd, input=input_data, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=20)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "dry_run": dry_run, "service": service}
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quiet default HTTP logs
        print("%s - %s" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/":
            data = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif route == "/api/config":
            write_json(self, load_config())
        elif route == "/api/options":
            write_json(self, {"voices": list_voices(), "sounds": list_sounds(), "config_path": str(CONFIG_PATH)})
        else:
            write_json(self, {"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        try:
            body = read_json_body(self)
            if route == "/api/config":
                write_json(self, {"ok": True, "config": save_config(body), "path": str(CONFIG_PATH)})
            elif route == "/api/test":
                write_json(self, run_notify_test(body))
            elif route == "/api/play-sound":
                sound = str(body.get("sound") or "")
                field = str(body.get("field") or "sample")
                result = play_sample(field, sound)
                write_json(self, result, 200 if result.get("ok") else 400)
            elif route == "/api/play-voice":
                voice = str(body.get("voice") or "")
                rate = str(body.get("rate") or "")
                text = str(body.get("text") or "Agentic Coding Notify")
                field = str(body.get("field") or "voice")
                result = play_voice_sample(field, voice, rate, text)
                write_json(self, result, 200 if result.get("ok") else 400)
            elif route == "/api/stop-voice":
                field = str(body.get("field") or "voice")
                write_json(self, {"ok": True, "field": field, "stopped": stop_samples(field)})
            elif route == "/api/stop-sound":
                field = str(body.get("field") or "all")
                write_json(self, {"ok": True, "field": field, "stopped": stop_samples(field)})
            else:
                write_json(self, {"error": "not found"}, 404)
        except Exception as exc:  # keep UI debuggable
            write_json(self, {"ok": False, "error": str(exc)}, 500)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"agentic-coding-notify UI running at {url}")
    print(f"config path: {CONFIG_PATH}")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
