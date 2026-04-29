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
      --plastic-0: #f4f1e8;
      --plastic-1: #ddd9cf;
      --plastic-2: #c9c5bb;
      --plastic-3: #a9a49a;
      --plastic-4: #6d6962;
      --ink: #24221d;
      --muted: #5c574f;
      --blue: #2f68d8;
      --green: #3f9449;
      --yellow: #f1bf28;
      --red: #dd3f46;
      --line: rgba(72, 68, 60, .42);
      --line-soft: rgba(72, 68, 60, .20);
      --bevel: inset 1px 1px 0 rgba(255,255,255,.82), inset -1px -1px 0 rgba(74,70,63,.28);
      font-family: var(--font-ui);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 0%, rgba(255,255,255,.58), transparent 25%),
        linear-gradient(135deg, #c5c1b7 0%, #e9e5dc 34%, #c0bbb0 100%);
      font-family: var(--font-ui);
      letter-spacing: -.01em;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .20;
      background-image:
        linear-gradient(rgba(54,50,44,.22) 1px, transparent 1px),
        linear-gradient(90deg, rgba(54,50,44,.18) 1px, transparent 1px);
      background-size: 18px 18px;
    }
    main { position: relative; padding: 14px 18px 22px; }
    .console {
      max-width: 1500px;
      margin: 0 auto;
      overflow: hidden;
      border: 1px solid #827d73;
      border-radius: 34px;
      background: linear-gradient(180deg, #e5e1d8 0%, #d0ccc2 56%, #c2bdb2 100%);
      box-shadow: var(--bevel), 0 18px 0 rgba(74,70,63,.24), 0 28px 58px rgba(64,60,54,.22);
    }
    .topbar {
      display: grid;
      grid-template-columns: 84px minmax(0, 1fr) auto auto;
      gap: 28px;
      align-items: center;
      min-height: 138px;
      padding: 30px 68px;
    }
    .stripe-stack { display: grid; gap: 8px; width: 62px; justify-self: center; }
    .stripe { height: 10px; border-radius: 999px; border: 1px solid rgba(36,33,29,.28); box-shadow: var(--bevel), 0 2px 4px rgba(74,70,63,.18); }
    .stripe.blue { background: var(--blue); }
    .stripe.green { background: var(--green); }
    .stripe.yellow { background: var(--yellow); }
    .stripe.red { background: var(--red); }
    h1 { margin: 0; font-family: var(--font-mono); font-size: clamp(34px, 4.4vw, 58px); line-height: .95; letter-spacing: -.07em; color: #25231e; text-shadow: 1px 1px 0 #fff9ec, 3px 3px 0 rgba(74,70,63,.16); }
    .subtitle { margin: 13px 0 0; color: var(--muted); font-family: var(--font-mono); font-size: 18px; letter-spacing: -.04em; }
    .status-module { min-width: 130px; padding: 14px 18px; text-align: center; border: 1px solid #7f7a70; border-radius: 10px; background: linear-gradient(180deg, #ebe8df, #d7d3c9); box-shadow: var(--bevel); font-family: var(--font-mono); }
    .status-module span { display: block; color: #5d574f; font-size: 16px; letter-spacing: .08em; }
    .status-module strong { display: block; color: var(--green); font-size: 23px; line-height: 1; margin-top: 4px; }
    .stop-top { display: grid; grid-template-columns: 54px auto; align-items: center; gap: 10px; min-height: 74px; padding: 8px 18px 8px 8px; border-radius: 12px; border: 1px solid #827d73; background: linear-gradient(180deg, #efede6, #cbc7bd); box-shadow: var(--bevel), 5px 5px 0 rgba(74,70,63,.32); color: var(--ink); font-family: var(--font-mono); font-size: 16px; text-align: left; text-transform: uppercase; }
    .stop-light { width: 42px; height: 42px; display: grid; place-items: center; border: 1px solid #8c867b; border-radius: 4px; background: linear-gradient(180deg, #f7f5ee, #c8c4ba); box-shadow: var(--bevel); }
    .stop-light i { width: 20px; height: 20px; background: var(--red); border: 1px solid #6b2b26; box-shadow: inset 1px 1px 0 rgba(255,255,255,.45); }
    .divider { height: 17px; border-top: 1px solid #817b70; border-bottom: 1px solid rgba(255,255,255,.62); background: linear-gradient(180deg, #c5c1b7, #aaa59a); position: relative; }
    .divider::after { content: ""; position: absolute; left: 50%; top: 1px; width: 72px; height: 13px; transform: translateX(-50%); background: repeating-linear-gradient(90deg, rgba(70,66,58,.52) 0 5px, transparent 5px 9px); }
    .deck { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; padding: 22px 26px; }
    .lower { grid-column: 1 / -1; display: grid; grid-template-columns: 1.1fr 1.1fr .9fr; gap: 24px; }
    .panel {
      position: relative;
      padding: 28px 30px 28px;
      min-height: 250px;
      border: 1px solid #837d72;
      border-radius: 12px;
      background:
        linear-gradient(180deg, rgba(255,253,247,.84), rgba(232,228,218,.82)),
        radial-gradient(circle at 15% 0%, rgba(255,255,255,.62), transparent 28%);
      box-shadow: var(--bevel), 4px 4px 0 rgba(74,70,63,.18);
    }
    .panel::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 8px; border-radius: 12px 0 0 12px; background: var(--accent-color, var(--blue)); box-shadow: inset 1px 0 0 rgba(255,255,255,.6); }
    .panel.voice { --accent-color: var(--blue); }
    .panel.sounds { --accent-color: var(--green); }
    .panel.text { --accent-color: var(--yellow); }
    .panel.preview-card { --accent-color: var(--blue); }
    .panel.disclosure { --accent-color: var(--red); }
    .panel-title { display: flex; align-items: baseline; gap: 16px; margin: 0 0 20px; font-family: var(--font-mono); }
    .panel-title .idx { color: var(--accent-color, var(--blue)); font-size: 25px; font-weight: 900; }
    .panel-title h2 { margin: 0; font-size: 25px; letter-spacing: -.05em; }
    label { display: block; margin: 15px 0 8px; font-family: var(--font-mono); font-weight: 800; color: #15130f; }
    .subtle { color: var(--muted); font-weight: 500; }
    .sample-note { margin-left: auto; color: var(--muted); font-family: var(--font-mono); font-size: 13px; }
    .field-line { display: flex; align-items: end; justify-content: space-between; gap: 12px; }
    .control-row { display: grid; grid-template-columns: minmax(0, 1fr) 70px; gap: 20px; align-items: center; }
    .search-field { position: relative; }
    .search-field::before { content: "⌕"; position: absolute; left: 17px; top: 50%; transform: translateY(-52%); color: #4e4a43; font-size: 30px; line-height: 1; z-index: 1; }
    input, textarea {
      width: 100%;
      border: 1px solid #8a8479;
      background: linear-gradient(180deg, rgba(255,255,252,.92), rgba(234,230,220,.84));
      color: var(--ink);
      border-radius: 10px;
      padding: 14px 44px 14px 52px;
      min-height: 54px;
      font: 20px var(--font-mono);
      letter-spacing: -.04em;
      outline: none;
      box-shadow: inset 1px 1px 0 rgba(255,255,255,.85), inset -1px -1px 0 rgba(74,70,63,.20);
    }
    input:focus, textarea:focus { border-color: var(--accent-color, var(--blue)); box-shadow: inset 1px 1px 0 rgba(255,255,255,.9), 0 0 0 3px rgba(47,104,216,.13); }
    input[list] { background-image: linear-gradient(45deg, transparent 50%, #5f5a52 50%), linear-gradient(135deg, #5f5a52 50%, transparent 50%), linear-gradient(180deg, rgba(255,255,252,.92), rgba(234,230,220,.84)); background-position: calc(100% - 24px) 25px, calc(100% - 16px) 25px, 0 0; background-size: 8px 8px, 8px 8px, 100% 100%; background-repeat: no-repeat; }
    textarea { min-height: 88px; resize: vertical; padding-left: 16px; }
    .field-stack { display: grid; gap: 10px; }
    .hint { margin: 17px 0 0; color: var(--muted); font-family: var(--font-mono); font-size: 14px; line-height: 1.45; }
    code, .mono, #rateLabel { font-family: var(--font-mono); }
    .rate-head { display: flex; justify-content: space-between; align-items: center; margin-top: 26px; }
    input[type="range"] { min-height: auto; padding: 0; border: 0; background: transparent; box-shadow: none; accent-color: var(--blue); }
    .range-scale { display: flex; justify-content: space-between; padding: 8px 2px 0; color: var(--muted); font-family: var(--font-mono); font-size: 13px; }
    button { cursor: pointer; font-family: var(--font-mono); font-weight: 900; }
    .icon-button { width: 70px; height: 62px; display: grid; place-items: center; padding: 0; border: 1px solid #827d73; border-radius: 8px; background: linear-gradient(180deg, #f2f0e8, #c8c4ba); color: var(--green); box-shadow: var(--bevel), 4px 4px 0 rgba(74,70,63,.22); }
    .icon-button:hover { transform: translateY(-1px); }
    .icon-button svg { width: 30px; height: 30px; stroke: currentColor; stroke-width: 2; fill: none; stroke-linecap: round; stroke-linejoin: round; }
    .icon-button.play svg { fill: currentColor; stroke: #1d4e24; }
    .icon-button .stop-icon { display: none; }
    .icon-button.is-playing { color: var(--red); }
    .icon-button.is-playing .play-icon { display: none; }
    .icon-button.is-playing .stop-icon { display: block; fill: currentColor; stroke: #6b2b26; }
    .preview-screen { position: relative; min-height: 204px; padding: 16px 68px 16px 18px; border: 1px solid #8a8479; border-radius: 8px; background-color: rgba(255,255,250,.62); background-image: linear-gradient(rgba(72,68,60,.06) 1px, transparent 1px), linear-gradient(90deg, rgba(72,68,60,.05) 1px, transparent 1px); background-size: 18px 18px; font: 17px var(--font-mono); box-shadow: inset 1px 1px 0 rgba(255,255,255,.82); }
    .preview-row { display: grid; grid-template-columns: 78px minmax(0,1fr); gap: 12px; margin: 3px 0; }
    .preview-row span { color: var(--blue); font-weight: 900; }
    .preview-row.green span { color: var(--green); }
    .preview-row b { font-weight: 500; overflow-wrap: anywhere; }
    .speaker-button { position: absolute; right: 12px; bottom: 10px; width: 54px; height: 44px; border: 1px solid #827d73; border-radius: 6px; background: linear-gradient(180deg, #f3f1e9, #cac6bc); box-shadow: var(--bevel), 2px 2px 0 rgba(74,70,63,.22); color: #302c26; }
    .info-box { display: grid; grid-template-columns: 52px 1fr; gap: 18px; align-items: start; font: 17px/1.45 var(--font-mono); }
    .info-icon { width: 50px; height: 46px; display: grid; place-items: center; border: 1px solid #837d72; border-radius: 6px; background: linear-gradient(180deg, #f4f2eb, #cbc7bd); box-shadow: var(--bevel); font: 900 28px var(--font-mono); }
    .footer { display: grid; grid-template-columns: 80px 1fr 1fr 1.05fr 1fr 80px; gap: 26px; align-items: center; padding: 30px 28px; border-top: 1px solid #817b70; background: linear-gradient(180deg, #d7d3ca, #c5c0b5); }
    .vent { height: 66px; background: repeating-linear-gradient(180deg, #736e65 0 4px, transparent 4px 12px); opacity: .75; border-radius: 6px; }
    .big-button { min-height: 76px; border: 1px solid #827d73; border-radius: 10px; box-shadow: var(--bevel), 5px 5px 0 rgba(74,70,63,.25); font-size: 17px; text-transform: uppercase; display: flex; align-items: center; justify-content: center; gap: 16px; color: var(--ink); background: linear-gradient(180deg, #f1eee6, #c9c5bb); }
    .big-button.primary { background: linear-gradient(180deg, #4c7fea, #2f62ce); color: #fff9ef; }
    .big-button.success { background: linear-gradient(180deg, #62ad68, #3d8c45); color: #fff9ef; }
    .big-button.preset { background: linear-gradient(180deg, #ffd95c, #edba25); }
    .button-icon { font-size: 30px; line-height: 1; }
    .sr-status { position: absolute; width: 1px; height: 1px; overflow: hidden; opacity: 0; pointer-events: none; }
    @media (max-width: 980px) {
      main { padding: 10px; }
      .topbar, .deck, .lower, .footer { grid-template-columns: 1fr; }
      .topbar { padding: 24px; }
      .stripe-stack, .status-module { justify-self: start; }
      .footer { gap: 14px; }
      .vent { display: none; }
    }
  </style>
</head>
<body>
<main>
  <div class="console">
    <header class="topbar">
      <div class="stripe-stack" aria-label="N64 gray palette">
        <i class="stripe blue"></i>
        <i class="stripe green"></i>
        <i class="stripe yellow"></i>
        <i class="stripe red"></i>
      </div>
      <div>
        <h1>agentic-coding-notify</h1>
        <p class="subtitle">Local notification preferences for agent apps and CLIs.</p>
      </div>
      <div class="status-module" aria-label="Status ready">
        <span>Status</span>
        <strong>READY</strong>
      </div>
      <button class="stop-top" onclick="stopAllSounds()">
        <span class="stop-light"><i></i></span>
        <span>Stop all<br>samples</span>
      </button>
    </header>
    <div class="divider" aria-hidden="true"></div>

    <div class="deck">
      <section class="panel voice">
        <div class="panel-title"><span class="idx">01</span><h2>Voice</h2></div>
        <div class="field-line">
          <label for="voice">Voice <span class="subtle">(type to search)</span></label>
          <span class="sample-note">Sample “Agentic Coding Notify”</span>
        </div>
        <div class="control-row">
          <div class="search-field">
            <input id="voice" list="voice_options" autocomplete="off" placeholder="Type to filter voices" />
            <datalist id="voice_options"></datalist>
          </div>
          <button id="voice_toggle" class="icon-button play" title="Play voice sample" aria-label="Play voice sample" onclick="toggleVoice()">
            <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
            <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
            <span class="sr-only">Play</span>
          </button>
        </div>
        <div class="rate-head">
          <label for="rate">Speech rate</label>
          <span id="rateLabel"></span>
        </div>
        <input id="rate" type="range" min="80" max="420" step="5" />
        <div class="range-scale"><span>100</span><span>200</span><span>300</span><span>400</span></div>
        <p class="hint">macOS <code>say -r</code> uses words per minute. <code>250</code> is roughly <code>1.25x</code> a <code>200</code> wpm baseline.</p>
      </section>

      <section class="panel sounds">
        <div class="panel-title"><span class="idx">02</span><h2>Sounds</h2></div>
        <div class="field-stack">
          <div>
            <label for="notification_sound">Notification sound <span class="subtle">(type to search)</span></label>
            <div class="control-row">
              <div class="search-field">
                <input id="notification_sound" list="sound_options" autocomplete="off" placeholder="Type to filter sounds" />
                <datalist id="sound_options"></datalist>
              </div>
              <button id="notification_sound_toggle" class="icon-button play" title="Play notification sample" aria-label="Play notification sample" onclick="toggleSound('notification_sound')">
                <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
                <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
                <span class="sr-only">Play</span>
              </button>
            </div>
          </div>
          <div>
            <label for="start_sound">Start sound <span class="subtle">(type to search)</span></label>
            <div class="control-row">
              <div class="search-field"><input id="start_sound" list="sound_options" autocomplete="off" placeholder="Type to filter sounds" /></div>
              <button id="start_sound_toggle" class="icon-button play" title="Play start sample" aria-label="Play start sample" onclick="toggleSound('start_sound')">
                <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
                <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
                <span class="sr-only">Play</span>
              </button>
            </div>
          </div>
          <div>
            <label for="end_sound">End sound <span class="subtle">(type to search)</span></label>
            <div class="control-row">
              <div class="search-field"><input id="end_sound" list="sound_options" autocomplete="off" placeholder="Type to filter sounds" /></div>
              <button id="end_sound_toggle" class="icon-button play" title="Play end sample" aria-label="Play end sample" onclick="toggleSound('end_sound')">
                <svg class="play-icon" viewBox="0 0 24 24" aria-hidden="true"><polygon points="8 5 19 12 8 19 8 5"></polygon></svg>
                <svg class="stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"></rect></svg>
                <span class="sr-only">Play</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <div class="lower">
        <section class="panel text">
          <div class="panel-title"><span class="idx">03</span><h2>Text</h2></div>
          <label for="app_voice_text_template">App template <span class="subtle">(type to search)</span></label>
          <div class="search-field"><input id="app_voice_text_template" list="template_options" autocomplete="off" /></div>
          <datalist id="template_options"></datalist>
          <label for="cli_voice_text_template">CLI template <span class="subtle">(type to search)</span></label>
          <div class="search-field"><input id="cli_voice_text_template" list="template_options" autocomplete="off" /></div>
          <label for="voice_text_template">Override spoken text <span class="subtle">(type to search)</span></label>
          <div class="search-field"><input id="voice_text_template" list="template_options" autocomplete="off" placeholder="(optional) custom text..." /></div>
        </section>

        <section class="panel preview-card">
          <div class="panel-title"><span class="idx">04</span><h2>Preview</h2></div>
          <div class="preview-screen">
            <div class="preview-row"><span>VOICE :</span><b id="previewVoice"></b></div>
            <div class="preview-row"><span>RATE :</span><b id="previewRate"></b></div>
            <div class="preview-row green"><span>NOTIF:</span><b id="previewNotification"></b></div>
            <div class="preview-row green"><span>START:</span><b id="previewStart"></b></div>
            <div class="preview-row green"><span>END :</span><b id="previewEnd"></b></div>
            <div class="preview-row"><span>TEXT :</span><b id="spokenPreview"></b></div>
            <div class="preview-row"><span>SERVICE:</span><b id="previewService"></b></div>
            <div class="preview-row"><span>TAB :</span><b id="previewTab"></b></div>
            <button class="speaker-button" title="Play voice sample" aria-label="Play voice sample from preview" onclick="playVoice()">🔊</button>
          </div>
          <p class="hint" id="soundPreview"></p>
          <label for="service">Service <span class="subtle">(type to search)</span></label>
          <div class="search-field"><input id="service" list="service_options" autocomplete="off" value="Claude App" placeholder="Type to filter services" /></div>
          <datalist id="service_options"></datalist>
          <label for="label">CLI tab label</label>
          <input id="label" value="review" />
          <label for="message">Notification message</label>
          <textarea id="message">Teste do agentic-coding-notify</textarea>
        </section>

        <section class="panel disclosure">
          <div class="panel-title"><span class="idx">05</span><h2>Disclosure</h2></div>
          <div class="info-box">
            <div class="info-icon">i</div>
            <p>Apps do not need terminal labels.<br><br>CLI sessions can use short tab labels like <code>One</code>, <code>Two</code>, or <code>Three</code>; the plugin already detects the service.</p>
          </div>
        </section>
      </div>
    </div>

    <div class="divider" aria-hidden="true"></div>
    <footer class="footer">
      <div class="vent"></div>
      <button class="big-button primary" onclick="saveConfig()"><span class="button-icon">💾</span> Save Config</button>
      <button class="big-button" onclick="testNotify(true)"><span class="button-icon">{}</span> Dry-run JSON</button>
      <button class="big-button success" onclick="testNotify(false)"><span class="button-icon">🔔</span> Real Notification</button>
      <button class="big-button preset" onclick="applyClassicPreset()"><span class="button-icon">☆</span> Classic Preset</button>
      <div class="vent"></div>
    </footer>
    <pre id="status" class="sr-status">Loading…</pre>
    <code id="configPath" class="sr-status"></code>
  </div>
</main>
<script>
const fields = ["voice", "rate", "notification_sound", "start_sound", "end_sound", "app_voice_text_template", "cli_voice_text_template", "voice_text_template"];
const soundFields = ["notification_sound", "start_sound", "end_sound"];
const serviceOptions = ["Claude App", "Codex App", "Claude CLI", "Codex CLI", "OpenCode CLI", "Pi CLI"];
const voiceSampleText = "Agentic Coding Notify";
const templateOptions = ["{service} App", "{service} {label}", "{service} CLI", "{voice_label}", "Agentic Coding Notify", ""];
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
function setPreviewText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}
function updatePreview() {
  const parts = selectedServiceParts();
  const rate = $("rate").value;
  setPreviewText("spokenPreview", computeSpokenPreview());
  setPreviewText("previewVoice", $("voice").value);
  setPreviewText("previewRate", `${rate} wpm (~${(Number(rate || 250) / 200).toFixed(2)}x)`);
  setPreviewText("previewNotification", $("notification_sound").value);
  setPreviewText("previewStart", $("start_sound").value);
  setPreviewText("previewEnd", $("end_sound").value);
  setPreviewText("previewService", parts.raw || "(auto)");
  setPreviewText("previewTab", $("label").value || "(auto)");
  $("soundPreview").textContent = `Voice: ${$("voice").value} @ ${rate} wpm · start: ${$("start_sound").value} · notification: ${$("notification_sound").value} · end: ${$("end_sound").value}`;
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
  fillDatalist("template_options", templateOptions);
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
