"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Power,
  Hand,
  MousePointer2,
  Send,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  X,
  Info,
} from "lucide-react";
import type { Stats } from "../models/status";
import type {
  AlertItem,
  ReminderItem,
  VisionStatus,
} from "../controllers/useHomeController";

type Controller = Readonly<{
  isPoweredOn: boolean;
  isSpeaking: boolean;
  isMicOn: boolean;
  isVolumeOn: boolean;
  lastCommand: string;
  isListening: boolean;
  transcript: string;
  alerts: AlertItem[];
  reminders: ReminderItem[];
  vision: VisionStatus;
  stats: Stats;
  handleToggle: (t: "power" | "mic" | "volume") => void;
  handleSpeak: () => void;
  handleListen: () => void;
  handleStopListening: () => void;
  toggleAirMouse: () => void;
  toggleSignLauncher: () => void;
  sendCommand: (text: string) => void;
  addReminderManual: (title: string, dueAt: string) => void;
  deleteReminder: (id: string) => void;
  clearTranscript: () => void;
}>;

const THEME = {
  ink: "#0f0f0f",
  muted: "#aaa",
  faint: "#e0d0d8",
  border: "#eddde6",
  bg: "#fdf8fb",
  accent: "#c8648a",
  pinkLight: "#f5e6ed",
};

const COMMAND_LIST = [
  {
    category: "🌐 Websites",
    commands: [
      "open browser",
      "open google",
      "open youtube",
      "open facebook",
      "open instagram",
      "open twitter",
      "open tiktok",
      "open reddit",
      "open discord",
      "open telegram",
      "open netflix",
      "open spotify",
      "open shopee",
      "open lazada",
      "open news",
    ],
  },
  {
    category: "🤖 AI Assistants",
    commands: [
      "open chatgpt",
      "open copilot",
      "open gemini",
      "open claude",
      "open perplexity",
    ],
  },
  {
    category: "📧 Productivity",
    commands: [
      "open gmail",
      "open google drive",
      "open google docs",
      "open google sheets",
      "open google calendar",
      "open windows calendar",
      "open notion",
      "open github",
    ],
  },
  {
    category: "💻 Windows Apps",
    commands: [
      "open notepad",
      "open calculator",
      "open file explorer",
      "open paint",
      "open task manager",
      "open settings",
      "open cmd",
      "open vs code",
      "open word",
      "open excel",
      "open powerpoint",
      "open teams",
      "open meet",
      "open camera",
      "open snipping tool",
    ],
  },
  {
    category: "🔊 Volume & Brightness",
    commands: [
      "volume up",
      "volume down",
      "mute",
      "unmute",
      "brightness up",
      "brightness down",
    ],
  },
  {
    category: "🖥️ Window Management",
    commands: [
      "minimize all",
      "show desktop",
      "close window",
      "switch window",
      "maximize",
      "minimize",
      "snap left",
      "snap right",
      "task view",
    ],
  },
  {
    category: "⚙️ System",
    commands: [
      "screenshot",
      "lock screen",
      "shutdown",
      "restart",
      "sleep system",
      "empty recycle bin",
      "cancel shutdown",
    ],
  },
  {
    category: "📊 System Info",
    commands: [
      "what time",
      "what date",
      "battery",
      "cpu usage",
      "ram usage",
      "ip address",
    ],
  },
  {
    category: "⏰ Reminders",
    commands: [
      "remind me to <task> in 10 minutes",
      "remind me to <task> at 5pm",
      "remind me to <task> tomorrow at 9am",
      "ipaalala mo na <task> pagkatapos ng 10 minuto",
      "list reminders",
    ],
  },
  {
    category: "📅 Calendar",
    commands: [
      "add event <title> tomorrow at 3pm",
      "schedule <title> on march 20 at 2pm",
      "mag-schedule ng <title> bukas ng 3pm",
      "i-schedule ang <title> ngayon ng 2pm",
    ],
  },
  {
    category: "👁️ Vision",
    commands: [
      "start air mouse",
      "stop air mouse",
      "start sign launcher",
      "stop sign launcher",
    ],
  },
  {
    category: "🔍 Search",
    commands: [
      "search <query>",
      "search <query> on youtube",
      "search <query> on spotify",
      "play <song>",
      "play <song> on spotify",
    ],
  },
];

// ── Alert helpers ────────────────────────────────────────────
function formatAlertMessage(message: string): string {
  if (!message) return message;
  const singleMatch = message.match(/^(.+?)\s*@\s*([\d\-T:+.Z]+)$/);
  if (singleMatch)
    return `${singleMatch[1].trim()} — ${fmtIso(singleMatch[2])}`;
  if (message.startsWith("Upcoming:")) {
    const lines = message
      .split(/\n|-(?=\s)/)
      .map((l) => l.trim())
      .filter(Boolean);
    const items = lines
      .slice(1)
      .map((line) => {
        const m = line.match(/^(.+?)\s*@\s*([\d\-T:+.Z]+)$/);
        return m
          ? `• ${m[1].trim()} — ${fmtIso(m[2])}`
          : line
            ? `• ${line}`
            : null;
      })
      .filter(Boolean);
    return items.length > 0 ? `${lines[0]}\n${items.join("\n")}` : message;
  }
  return message.replace(
    /\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+\-]\d{2}:\d{2}|Z)?)\b/g,
    (_, iso) => fmtIso(iso),
  );
}
function fmtIso(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ── Modal base ───────────────────────────────────────────────
const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.35)",
  zIndex: 100,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 16,
};
const sheetStyle: React.CSSProperties = {
  background: "#fff",
  width: "100%",
  maxWidth: 440,
  borderRadius: 4,
  border: `1px solid ${THEME.border}`,
  maxHeight: "90vh",
  overflowY: "auto",
};

function ModalHeader({
  icon,
  title,
  onClose,
}: {
  icon: React.ReactNode;
  title: string;
  onClose: () => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 20px",
        borderBottom: `1px solid ${THEME.border}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {icon}
        <span
          style={{
            fontFamily: "'Courier New', monospace",
            fontSize: 11,
            letterSpacing: 4,
            textTransform: "uppercase",
            color: THEME.ink,
          }}
        >
          {title}
        </span>
      </div>
      <button
        onClick={onClose}
        style={{
          border: "none",
          background: "transparent",
          cursor: "pointer",
          padding: 4,
          display: "flex",
          alignItems: "center",
        }}
      >
        <X size={14} color={THEME.muted} />
      </button>
    </div>
  );
}

function StepList({ steps }: { steps: string[] }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        marginBottom: 20,
      }}
    >
      {steps.map((text, i) => (
        <div
          key={i}
          style={{ display: "flex", gap: 12, alignItems: "flex-start" }}
        >
          <span
            style={{
              minWidth: 22,
              height: 22,
              borderRadius: "50%",
              background: THEME.ink,
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 10,
              fontFamily: "'Courier New', monospace",
              flexShrink: 0,
            }}
          >
            {i + 1}
          </span>
          <span
            style={{
              fontSize: 13,
              color: THEME.ink,
              lineHeight: 1.5,
              paddingTop: 2,
            }}
          >
            {text}
          </span>
        </div>
      ))}
    </div>
  );
}

function GestureGrid({
  items,
}: {
  items: { emoji: string; label: string; action: string }[];
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 8,
        marginBottom: 20,
      }}
    >
      {items.map((g) => (
        <div
          key={g.label}
          style={{
            border: `1px solid ${THEME.border}`,
            borderRadius: 2,
            padding: "10px 12px",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span style={{ fontSize: 22, lineHeight: 1 }}>{g.emoji}</span>
          <div>
            <div style={{ fontSize: 12, color: THEME.ink, fontWeight: 500 }}>
              {g.label}
            </div>
            <div style={{ fontSize: 11, color: THEME.muted }}>{g.action}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Tip({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: THEME.pinkLight,
        border: `1px solid ${THEME.border}`,
        borderRadius: 2,
        padding: "10px 12px",
        fontSize: 12,
        color: THEME.ink,
        marginBottom: 12,
        lineHeight: 1.5,
      }}
    >
      {children}
    </div>
  );
}

// ── Air Mouse Modal ──────────────────────────────────────────
function AirMouseModal({
  onClose,
  onToggle,
  isActive,
}: {
  onClose: () => void;
  onToggle: () => void;
  isActive: boolean;
}) {
  return (
    <div
      style={overlayStyle}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={sheetStyle}>
        <ModalHeader
          icon={<MousePointer2 size={16} color={THEME.ink} />}
          title="Air Mouse"
          onClose={onClose}
        />
        <div style={{ padding: 20 }}>
          <div
            style={{
              fontFamily: "'Courier New', monospace",
              fontSize: 9,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: THEME.muted,
              marginBottom: 10,
            }}
          >
            Paano gamitin
          </div>
          <StepList
            steps={[
              "Siguraduhing naka-on ang camera at maliwanag ang background.",
              "I-click ang Start Air Mouse button sa ibaba.",
              "Itaas ang index finger mo sa harap ng camera — ito ang pointer ng cursor.",
              "I-pinch ang index finger at thumb nang mabilis para mag-left click.",
              "Ang ideal na distansya ay 30–60 cm mula sa camera.",
            ]}
          />
          <div
            style={{
              fontFamily: "'Courier New', monospace",
              fontSize: 9,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: THEME.muted,
              marginBottom: 10,
            }}
          >
            Hand gestures
          </div>
          <GestureGrid
            items={[
              { emoji: "☝️", label: "Index finger up", action: "Move cursor" },
              {
                emoji: "🤌",
                label: "Pinch (index + thumb)",
                action: "Left click",
              },
              { emoji: "✌️", label: "Two fingers up", action: "Scroll mode" },
              { emoji: "✊", label: "Fist", action: "Pause / freeze cursor" },
            ]}
          />
          <Tip>
            <strong>Tip:</strong> Mag-ensure ng maliwanag na ilaw sa harapan mo
            at walang masyadong galaw sa background para mas accurate ang hand
            tracking.
          </Tip>
          <Tip>
            <strong>Distansya:</strong> Hindi gumagana nang maayos kung
            masyadong malayo o malapit sa camera. Subukan ang 40–50 cm.
          </Tip>
          <button
            onClick={() => {
              onToggle();
              onClose();
            }}
            style={{
              width: "100%",
              padding: "12px 0",
              border: `1px solid ${isActive ? "#ccc" : THEME.ink}`,
              borderRadius: 2,
              background: isActive ? "transparent" : THEME.ink,
              color: isActive ? THEME.muted : "#fff",
              fontSize: 10,
              letterSpacing: 4,
              textTransform: "uppercase",
              fontFamily: "'Courier New', monospace",
              cursor: "pointer",
            }}
          >
            {isActive ? "Stop Air Mouse" : "Start Air Mouse"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Sign Launcher Modal ──────────────────────────────────────
function SignLauncherModal({
  onClose,
  onToggle,
  isActive,
}: {
  onClose: () => void;
  onToggle: () => void;
  isActive: boolean;
}) {
  return (
    <div
      style={overlayStyle}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={sheetStyle}>
        <ModalHeader
          icon={<Hand size={16} color={THEME.ink} />}
          title="Sign Launcher"
          onClose={onClose}
        />
        <div style={{ padding: 20 }}>
          <div
            style={{
              fontFamily: "'Courier New', monospace",
              fontSize: 9,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: THEME.muted,
              marginBottom: 10,
            }}
          >
            Paano gamitin
          </div>
          <StepList
            steps={[
              "I-click ang Start Sign Launcher button sa ibaba.",
              "Ipakita ang iyong kamay nang malinaw sa harap ng camera.",
              "Gawin ang isang hand sign mula sa listahan sa ibaba.",
              "Hawakan ang pose nang 1–2 segundo hanggang marinig ang confirmation ni FRIDAY.",
              "Isang sign lang sa isang pagkakataon — huwag palipat-lipat nang mabilis.",
            ]}
          />
          <div
            style={{
              fontFamily: "'Courier New', monospace",
              fontSize: 9,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: THEME.muted,
              marginBottom: 10,
            }}
          >
            Hand signs → aksyon
          </div>
          <GestureGrid
            items={[
              { emoji: "👍", label: "Thumbs up", action: "Open browser" },
              { emoji: "✌️", label: "Peace / V sign", action: "Open YouTube" },
              { emoji: "🖐️", label: "Open palm", action: "Open Spotify" },
              { emoji: "👌", label: "OK sign", action: "Open Settings" },
              { emoji: "☝️", label: "Index up", action: "Volume up" },
              { emoji: "👇", label: "Index down", action: "Volume down" },
              { emoji: "👈", label: "Point left", action: "Previous / Back" },
              { emoji: "👉", label: "Point right", action: "Next / Forward" },
              { emoji: "✊", label: "Fist", action: "Close window" },
              { emoji: "🤙", label: "Shaka / Call me", action: "Open dialer" },
            ]}
          />
          <Tip>
            <strong>Tip:</strong> Mag-practice muna ng isa-isa bago gamitin
            tuloy-tuloy. Mas maganda kung iisa lang ang kamay na nakikita ng
            camera.
          </Tip>
          <Tip>
            <strong>Note:</strong> Ang mga sign na ito ay base sa default
            config. Tingnan ang{" "}
            <code
              style={{
                fontFamily: "'Courier New', monospace",
                fontSize: 11,
                background: THEME.border,
                padding: "1px 4px",
                borderRadius: 2,
              }}
            >
              sign_launcher.py
            </code>{" "}
            para sa exact na mapping ng gestures sa iyong project.
          </Tip>
          <button
            onClick={() => {
              onToggle();
              onClose();
            }}
            style={{
              width: "100%",
              padding: "12px 0",
              border: `1px solid ${isActive ? "#ccc" : THEME.ink}`,
              borderRadius: 2,
              background: isActive ? "transparent" : THEME.ink,
              color: isActive ? THEME.muted : "#fff",
              fontSize: 10,
              letterSpacing: 4,
              textTransform: "uppercase",
              fontFamily: "'Courier New', monospace",
              cursor: "pointer",
            }}
          >
            {isActive ? "Stop Sign Launcher" : "Start Sign Launcher"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Shared components ────────────────────────────────────────
function BouncingDots({
  active,
  color = THEME.ink,
  count = 5,
}: {
  active: boolean;
  color?: string;
  count?: number;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 5,
        height: 32,
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: color,
            opacity: active ? 1 : 0.2,
            animation: active
              ? `bounce-dot 1.1s ease-in-out ${i * 0.12}s infinite`
              : "none",
            transition: "opacity 0.4s ease",
          }}
        />
      ))}
    </div>
  );
}

function CoreIndicator({
  active,
  speaking,
  listening,
}: {
  active: boolean;
  speaking: boolean;
  listening: boolean;
}) {
  const isAnimating = active && (speaking || listening);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 20,
        width: 200,
      }}
    >
      <div
        style={{
          position: "relative",
          width: 160,
          height: 160,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            position: "absolute",
            width: 160,
            height: 160,
            borderRadius: "50%",
            border: `1px solid ${active ? THEME.ink : THEME.border}`,
            transition: "border-color 0.6s ease",
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 120,
            height: 120,
            borderRadius: "50%",
            border: `1px solid ${active ? THEME.faint : "transparent"}`,
            transition: "border-color 0.6s ease",
            animation:
              listening && active ? "slow-spin 12s linear infinite" : "none",
          }}
        />
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: active ? THEME.ink : THEME.faint,
            transition: "all 0.5s ease",
            animation: isAnimating
              ? "breathe 1.6s ease-in-out infinite"
              : "none",
          }}
        />
        {isAnimating && (
          <div
            style={{
              position: "absolute",
              width: 180,
              height: 180,
              borderRadius: "50%",
              border: `1px solid ${THEME.faint}`,
              animation: "expand-fade 1.8s ease-out infinite",
            }}
          />
        )}
      </div>
      <div style={{ height: 32 }}>
        {speaking && <BouncingDots active color={THEME.accent} count={7} />}
        {listening && !speaking && (
          <BouncingDots active color={THEME.accent} count={5} />
        )}
        {!listening && !speaking && (
          <BouncingDots active={false} color={THEME.muted} count={5} />
        )}
      </div>
      <div
        style={{
          fontFamily: "'Courier New', monospace",
          fontSize: 9,
          letterSpacing: 4,
          textTransform: "uppercase",
          color: speaking ? THEME.accent : listening ? THEME.ink : THEME.muted,
          transition: "color 0.4s ease",
          marginTop: -10,
        }}
      >
        {speaking
          ? "speaking"
          : listening
            ? "listening"
            : active
              ? "ready"
              : "offline"}
      </div>
    </div>
  );
}

function ControlBtn({
  onClick,
  children,
  active,
}: {
  onClick: () => void;
  children: React.ReactNode;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        width: 44,
        height: 44,
        borderRadius: "50%",
        border: `1px solid ${active ? THEME.ink : THEME.border}`,
        background: active ? THEME.ink : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        transition: "all 0.2s ease",
      }}
    >
      {children}
    </button>
  );
}

// ── Main View ────────────────────────────────────────────────
export default function HomeView(props: { controller: Controller }) {
  const c = props.controller;
  const [time, setTime] = useState("");
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({});
  const [manualCmd, setManualCmd] = useState("");
  const [reminderTitle, setReminderTitle] = useState("");
  const [reminderDate, setReminderDate] = useState("");
  const [reminderTime, setReminderTime] = useState("");
  const [showReminderForm, setShowReminderForm] = useState(false);
  const [showCommands, setShowCommands] = useState(false);
  const [showAirMouseModal, setShowAirMouseModal] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);
  const cmdInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const tick = () =>
      setTime(
        new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const topAlerts = (c.alerts || [])
    .filter((a) => a?.id && !dismissed[a.id])
    .slice(-3)
    .reverse();

  const fmtDue = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("en-US", {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const handleManualCommand = () => {
    if (!manualCmd.trim()) return;
    c.sendCommand(manualCmd.trim());
    setManualCmd("");
  };

  const handleAddReminder = () => {
    if (!reminderTitle.trim() || !reminderDate || !reminderTime) return;
    c.addReminderManual(
      reminderTitle.trim(),
      new Date(`${reminderDate}T${reminderTime}`).toISOString(),
    );
    setReminderTitle("");
    setReminderDate("");
    setReminderTime("");
    setShowReminderForm(false);
  };

  const handleCommandClick = (cmd: string) => {
    setManualCmd(cmd);
    setTimeout(() => {
      const input = cmdInputRef.current;
      if (!input) return;
      input.focus();
      const ph = cmd.match(/<[^>]+>/);
      if (ph) {
        const s = cmd.indexOf(ph[0]);
        input.setSelectionRange(s, s + ph[0].length);
      }
    }, 50);
  };

  const inputStyle: React.CSSProperties = {
    border: `1px solid ${THEME.border}`,
    background: THEME.bg,
    padding: "10px 12px",
    fontSize: 12,
    color: THEME.ink,
    fontFamily: "'Courier New', monospace",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };
  const alertBg = (l: string) =>
    ({ error: "#fff5f5", reminder: "#fff8f0", warning: "#fffbf0" })[l] ??
    "#fff";
  const alertDot = (l: string) =>
    ({ error: "#e05c5c", reminder: THEME.accent, warning: "#d49a30" })[l] ??
    THEME.ink;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: THEME.bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Georgia', serif",
        padding: "24px",
      }}
    >
      {showAirMouseModal && (
        <AirMouseModal
          onClose={() => setShowAirMouseModal(false)}
          onToggle={c.toggleAirMouse}
          isActive={c.vision.airMouse}
        />
      )}
      {showSignModal && (
        <SignLauncherModal
          onClose={() => setShowSignModal(false)}
          onToggle={c.toggleSignLauncher}
          isActive={c.vision.signLauncher}
        />
      )}

      {/* Toasts */}
      <div
        style={{
          position: "fixed",
          top: 16,
          left: "50%",
          transform: "translateX(-50%)",
          width: "min(520px, calc(100vw - 32px))",
          zIndex: 50,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          pointerEvents: "none",
        }}
      >
        {topAlerts.map((a) => {
          const lines = (a.message ? formatAlertMessage(a.message) : "").split(
            "\n",
          );
          return (
            <button
              key={a.id}
              onClick={() => setDismissed((p) => ({ ...p, [a.id]: true }))}
              style={{
                pointerEvents: "auto",
                textAlign: "left",
                border: `1px solid ${THEME.border}`,
                background: alertBg(a.level),
                padding: "10px 12px",
                borderRadius: 2,
                cursor: "pointer",
                width: "100%",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: alertDot(a.level),
                    flexShrink: 0,
                  }}
                />
                <span
                  style={{
                    fontFamily: "'Courier New', monospace",
                    fontSize: 10,
                    letterSpacing: 3,
                    textTransform: "uppercase",
                    color: THEME.ink,
                    flex: 1,
                  }}
                >
                  {a.title || a.level}
                </span>
                <X size={11} color={THEME.muted} />
              </div>
              {lines.length > 0 && (
                <div
                  style={{
                    marginTop: 6,
                    paddingLeft: 15,
                    display: "flex",
                    flexDirection: "column",
                    gap: 2,
                  }}
                >
                  {lines.map((line, i) => (
                    <div key={i} style={{ fontSize: 12, color: THEME.ink }}>
                      {line}
                    </div>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>

      <div style={{ width: "100%", maxWidth: 520 }}>
        <div style={{ marginBottom: 48, textAlign: "center" }}>
          <p
            style={{
              fontSize: 11,
              letterSpacing: 6,
              color: THEME.muted,
              textTransform: "uppercase",
              marginBottom: 8,
              fontFamily: "'Courier New', monospace",
            }}
          >
            {time}
          </p>
          <h1
            style={{
              fontSize: 32,
              fontWeight: 400,
              letterSpacing: 16,
              color: THEME.ink,
              textTransform: "uppercase",
              margin: 0,
            }}
          >
            FRIDAY
          </h1>
        </div>

        <div
          style={{
            border: `1px solid ${THEME.border}`,
            borderRadius: 2,
            padding: "48px 32px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 40,
            background: "#fff",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              width: "100%",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: c.isPoweredOn ? "#3a3a3a" : THEME.faint,
                transition: "background 0.4s ease",
              }}
            />
            <span
              style={{
                fontSize: 10,
                letterSpacing: 4,
                color: c.isPoweredOn ? THEME.ink : THEME.muted,
                fontFamily: "'Courier New', monospace",
                textTransform: "uppercase",
                transition: "color 0.4s ease",
              }}
            >
              {c.isSpeaking
                ? "speaking"
                : c.isListening
                  ? "listening"
                  : c.isPoweredOn
                    ? "online"
                    : "offline"}
            </span>
          </div>

          <CoreIndicator
            active={c.isPoweredOn}
            speaking={c.isSpeaking}
            listening={c.isListening}
          />

          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <ControlBtn
              onClick={() => c.handleToggle("power")}
              active={c.isPoweredOn}
            >
              <Power size={16} color={c.isPoweredOn ? "#fff" : THEME.muted} />
            </ControlBtn>
            <ControlBtn
              onClick={() => c.handleToggle("mic")}
              active={c.isMicOn}
            >
              {c.isMicOn ? (
                <Mic size={16} color="#fff" />
              ) : (
                <MicOff size={16} color={THEME.muted} />
              )}
            </ControlBtn>
            <ControlBtn
              onClick={() => c.handleToggle("volume")}
              active={c.isVolumeOn}
            >
              {c.isVolumeOn ? (
                <Volume2 size={16} color="#fff" />
              ) : (
                <VolumeX size={16} color={THEME.muted} />
              )}
            </ControlBtn>
          </div>

          <button
            onClick={c.isListening ? c.handleStopListening : c.handleListen}
            style={{
              width: "100%",
              padding: "14px 0",
              border: `1px solid ${c.isListening ? "#ccc" : THEME.ink}`,
              borderRadius: 2,
              background: c.isListening ? "transparent" : THEME.ink,
              color: c.isListening ? THEME.muted : "#fff",
              fontSize: 10,
              letterSpacing: 5,
              textTransform: "uppercase",
              fontFamily: "'Courier New', monospace",
              cursor: "pointer",
              transition: "all 0.3s ease",
            }}
          >
            {c.isListening ? "terminate" : "activate"}
          </button>

          {/* Speech to text */}
          <div style={{ width: "100%" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 6,
              }}
            >
              <div
                style={{
                  fontFamily: "'Courier New', monospace",
                  fontSize: 10,
                  letterSpacing: 3,
                  textTransform: "uppercase",
                  color: THEME.muted,
                }}
              >
                speech-to-text
              </div>
              {!!c.transcript && (
                <button
                  onClick={c.clearTranscript}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 3,
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    fontFamily: "'Courier New', monospace",
                    fontSize: 9,
                    letterSpacing: 2,
                    textTransform: "uppercase",
                    color: THEME.muted,
                    padding: 0,
                  }}
                >
                  <X size={10} /> clear
                </button>
              )}
            </div>
            <div
              style={{
                border: `1px solid ${c.isListening ? THEME.ink : THEME.border}`,
                background: THEME.bg,
                padding: "10px 12px",
                fontSize: 12,
                color: THEME.ink,
                minHeight: 42,
                whiteSpace: "pre-wrap",
                transition: "border-color 0.3s ease",
              }}
            >
              {c.transcript || (c.isListening ? "Listening…" : "—")}
            </div>
            {!!c.lastCommand && (
              <div style={{ marginTop: 8, fontSize: 11, color: THEME.muted }}>
                Last command: {c.lastCommand}
              </div>
            )}
          </div>

          {/* Manual command */}
          <div style={{ width: "100%" }}>
            <div
              style={{
                fontFamily: "'Courier New', monospace",
                fontSize: 10,
                letterSpacing: 3,
                textTransform: "uppercase",
                color: THEME.muted,
                marginBottom: 6,
              }}
            >
              manual command
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                ref={cmdInputRef}
                value={manualCmd}
                onChange={(e) => setManualCmd(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleManualCommand()}
                placeholder='Type a command, e.g. "open youtube"'
                style={{ ...inputStyle, flex: 1 }}
              />
              <button
                onClick={handleManualCommand}
                style={{
                  padding: "10px 14px",
                  border: `1px solid ${THEME.ink}`,
                  borderRadius: 2,
                  background: THEME.ink,
                  color: "#fff",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <Send size={14} color="#fff" />
              </button>
            </div>

            <button
              onClick={() => setShowCommands((v) => !v)}
              style={{
                marginTop: 8,
                display: "flex",
                alignItems: "center",
                gap: 6,
                border: "none",
                background: "transparent",
                cursor: "pointer",
                fontFamily: "'Courier New', monospace",
                fontSize: 9,
                letterSpacing: 3,
                textTransform: "uppercase",
                color: THEME.muted,
                padding: 0,
              }}
            >
              {showCommands ? (
                <ChevronUp size={12} />
              ) : (
                <ChevronDown size={12} />
              )}
              {showCommands ? "hide commands" : "show available commands"}
            </button>

            {showCommands && (
              <div
                style={{
                  marginTop: 8,
                  border: `1px solid ${THEME.border}`,
                  background: THEME.bg,
                  padding: "12px",
                  maxHeight: 420,
                  overflowY: "auto",
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                }}
              >
                {/* ── Wake Word Notice ── */}
                <div
                  style={{
                    border: `1px solid ${THEME.accent}`,
                    borderRadius: 2,
                    background: THEME.pinkLight,
                    padding: "12px 14px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 8,
                    }}
                  >
                    {/* small lock/key icon using unicode */}
                    <span style={{ fontSize: 13 }}>🔑</span>
                    <span
                      style={{
                        fontFamily: "'Courier New', monospace",
                        fontSize: 9,
                        letterSpacing: 3,
                        textTransform: "uppercase",
                        color: THEME.accent,
                        fontWeight: 600,
                      }}
                    >
                      Wake Word Required
                    </span>
                  </div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: 12,
                      color: THEME.ink,
                      lineHeight: 1.6,
                      fontFamily: "'Georgia', serif",
                    }}
                  >
                    Prior to issuing any voice command, FRIDAY must first be
                    addressed by its designated wake phrase. This initiates the
                    system&apos;s active listening session.
                  </p>

                  {/* Wake word chip */}
                  <div
                    style={{
                      marginTop: 10,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "'Courier New', monospace",
                        fontSize: 9,
                        letterSpacing: 3,
                        textTransform: "uppercase",
                        color: THEME.muted,
                      }}
                    >
                      Wake phrase:
                    </span>
                    <button
                      onClick={() => handleCommandClick("hey friday")}
                      style={{
                        padding: "4px 12px",
                        border: `1px solid ${THEME.ink}`,
                        background: THEME.ink,
                        color: "#fff",
                        borderRadius: 2,
                        cursor: "pointer",
                        fontFamily: "'Courier New', monospace",
                        fontSize: 11,
                        letterSpacing: 3,
                        textTransform: "uppercase",
                      }}
                      title="Click to use as command"
                    >
                      hey friday
                    </button>
                  </div>

                  {/* Usage example */}
                  <div
                    style={{
                      marginTop: 12,
                      borderTop: `1px solid ${THEME.border}`,
                      paddingTop: 10,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: "'Courier New', monospace",
                        fontSize: 9,
                        letterSpacing: 3,
                        textTransform: "uppercase",
                        color: THEME.muted,
                        marginBottom: 6,
                      }}
                    >
                      Correct invocation sequence
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                      }}
                    >
                      {[
                        {
                          step: "01",
                          label: "Initiate session",
                          cmd: "hey friday",
                        },
                        {
                          step: "02",
                          label: "Issue command",
                          cmd: "open youtube",
                        },
                      ].map(({ step, label, cmd }) => (
                        <div
                          key={step}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                          }}
                        >
                          <span
                            style={{
                              fontFamily: "'Courier New', monospace",
                              fontSize: 9,
                              color: THEME.muted,
                              letterSpacing: 2,
                              minWidth: 20,
                            }}
                          >
                            {step}
                          </span>
                          <span
                            style={{
                              fontSize: 11,
                              color: THEME.muted,
                              fontFamily: "'Georgia', serif",
                              minWidth: 110,
                            }}
                          >
                            {label}
                          </span>
                          <code
                            style={{
                              fontFamily: "'Courier New', monospace",
                              fontSize: 11,
                              background: "#fff",
                              border: `1px solid ${THEME.border}`,
                              padding: "2px 8px",
                              borderRadius: 2,
                              color: THEME.ink,
                            }}
                          >
                            {cmd}
                          </code>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Note about manual command */}
                  <div
                    style={{
                      marginTop: 10,
                      fontSize: 11,
                      color: THEME.muted,
                      fontFamily: "'Georgia', serif",
                      lineHeight: 1.5,
                      fontStyle: "italic",
                    }}
                  >
                    Note: The wake phrase is only required for voice input.
                    Manual commands submitted via the text field above are
                    processed immediately without a prior invocation.
                  </div>
                </div>

                {/* ── Command categories ── */}
                {COMMAND_LIST.map((group) => (
                  <div key={group.category}>
                    <div
                      style={{
                        fontFamily: "'Courier New', monospace",
                        fontSize: 9,
                        letterSpacing: 3,
                        textTransform: "uppercase",
                        color: THEME.accent,
                        marginBottom: 6,
                      }}
                    >
                      {group.category}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {group.commands.map((cmd) => (
                        <button
                          key={cmd}
                          onClick={() => handleCommandClick(cmd)}
                          style={{
                            padding: "4px 8px",
                            border: `1px solid ${THEME.border}`,
                            background: "#fff",
                            borderRadius: 2,
                            cursor: "pointer",
                            fontFamily: "'Courier New', monospace",
                            fontSize: 10,
                            color: cmd.includes("<") ? THEME.accent : THEME.ink,
                            transition: "all 0.15s ease",
                          }}
                          title={
                            cmd.includes("<")
                              ? "Click to fill in template"
                              : `Click to use: ${cmd}`
                          }
                        >
                          {cmd}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Reminders */}
          <div style={{ width: "100%" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 6,
              }}
            >
              <div
                style={{
                  fontFamily: "'Courier New', monospace",
                  fontSize: 10,
                  letterSpacing: 3,
                  textTransform: "uppercase",
                  color: THEME.muted,
                }}
              >
                reminders
              </div>
              <button
                onClick={() => setShowReminderForm((v) => !v)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  border: `1px solid ${THEME.border}`,
                  background: "transparent",
                  padding: "4px 10px",
                  borderRadius: 2,
                  cursor: "pointer",
                  fontFamily: "'Courier New', monospace",
                  fontSize: 9,
                  letterSpacing: 2,
                  textTransform: "uppercase",
                  color: THEME.ink,
                }}
              >
                <Plus size={11} /> add
              </button>
            </div>
            {showReminderForm && (
              <div
                style={{
                  border: `1px solid ${THEME.border}`,
                  background: THEME.pinkLight,
                  padding: "12px",
                  marginBottom: 8,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  borderRadius: 2,
                }}
              >
                <input
                  value={reminderTitle}
                  onChange={(e) => setReminderTitle(e.target.value)}
                  placeholder="Title (e.g. Take medicine)"
                  style={inputStyle}
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="date"
                    value={reminderDate}
                    onChange={(e) => setReminderDate(e.target.value)}
                    style={{ ...inputStyle, flex: 1 }}
                  />
                  <input
                    type="time"
                    value={reminderTime}
                    onChange={(e) => setReminderTime(e.target.value)}
                    style={{ ...inputStyle, flex: 1 }}
                  />
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={handleAddReminder}
                    style={{
                      flex: 1,
                      padding: "8px 0",
                      border: `1px solid ${THEME.ink}`,
                      background: THEME.ink,
                      color: "#fff",
                      borderRadius: 2,
                      cursor: "pointer",
                      fontFamily: "'Courier New', monospace",
                      fontSize: 10,
                      letterSpacing: 3,
                      textTransform: "uppercase",
                    }}
                  >
                    save
                  </button>
                  <button
                    onClick={() => setShowReminderForm(false)}
                    style={{
                      flex: 1,
                      padding: "8px 0",
                      border: `1px solid ${THEME.border}`,
                      background: "transparent",
                      color: THEME.muted,
                      borderRadius: 2,
                      cursor: "pointer",
                      fontFamily: "'Courier New', monospace",
                      fontSize: 10,
                      letterSpacing: 3,
                      textTransform: "uppercase",
                    }}
                  >
                    cancel
                  </button>
                </div>
              </div>
            )}
            <div
              style={{
                border: `1px solid ${THEME.border}`,
                background: "#fff",
                padding: "10px 12px",
                fontSize: 12,
                color: THEME.ink,
              }}
            >
              {(c.reminders || []).length === 0 ? (
                <div style={{ color: THEME.muted }}>No upcoming reminders.</div>
              ) : (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 8 }}
                >
                  {c.reminders.slice(0, 5).map((r) => (
                    <div
                      key={r.id}
                      style={{ display: "flex", alignItems: "center", gap: 10 }}
                    >
                      <span
                        style={{
                          width: 110,
                          color: THEME.muted,
                          fontSize: 11,
                          flexShrink: 0,
                        }}
                      >
                        {fmtDue(r.dueAt)}
                      </span>
                      <span style={{ flex: 1 }}>{r.title}</span>
                      <button
                        onClick={() => c.deleteReminder(r.id)}
                        style={{
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          padding: 2,
                          display: "flex",
                          alignItems: "center",
                        }}
                      >
                        <Trash2 size={12} color={THEME.muted} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Vision toggles */}
          <div style={{ width: "100%", display: "flex", gap: 10 }}>
            <div style={{ flex: 1, display: "flex" }}>
              <button
                onClick={c.toggleAirMouse}
                style={{
                  flex: 1,
                  padding: "10px 12px",
                  border: `1px solid ${THEME.border}`,
                  borderRight: "none",
                  background: c.vision.airMouse ? THEME.ink : "#fff",
                  color: c.vision.airMouse ? "#fff" : THEME.ink,
                  borderRadius: "2px 0 0 2px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  fontFamily: "'Courier New', monospace",
                  fontSize: 10,
                  letterSpacing: 3,
                  textTransform: "uppercase",
                }}
              >
                <MousePointer2
                  size={14}
                  color={c.vision.airMouse ? "#fff" : THEME.ink}
                />{" "}
                air mouse
              </button>
              <button
                onClick={() => setShowAirMouseModal(true)}
                title="How to use Air Mouse"
                style={{
                  padding: "0 11px",
                  border: `1px solid ${THEME.border}`,
                  background: c.vision.airMouse ? THEME.ink : THEME.bg,
                  borderRadius: "0 2px 2px 0",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <Info
                  size={13}
                  color={c.vision.airMouse ? "#fff" : THEME.muted}
                />
              </button>
            </div>
            <div style={{ flex: 1, display: "flex" }}>
              <button
                onClick={c.toggleSignLauncher}
                style={{
                  flex: 1,
                  padding: "10px 12px",
                  border: `1px solid ${THEME.border}`,
                  borderRight: "none",
                  background: c.vision.signLauncher ? THEME.ink : "#fff",
                  color: c.vision.signLauncher ? "#fff" : THEME.ink,
                  borderRadius: "2px 0 0 2px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  fontFamily: "'Courier New', monospace",
                  fontSize: 10,
                  letterSpacing: 3,
                  textTransform: "uppercase",
                }}
              >
                <Hand
                  size={14}
                  color={c.vision.signLauncher ? "#fff" : THEME.ink}
                />{" "}
                sign launcher
              </button>
              <button
                onClick={() => setShowSignModal(true)}
                title="How to use Sign Launcher"
                style={{
                  padding: "0 11px",
                  border: `1px solid ${THEME.border}`,
                  background: c.vision.signLauncher ? THEME.ink : THEME.bg,
                  borderRadius: "0 2px 2px 0",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <Info
                  size={13}
                  color={c.vision.signLauncher ? "#fff" : THEME.muted}
                />
              </button>
            </div>
          </div>

          <div style={{ width: "100%", fontSize: 11, color: THEME.muted }}>
            Voice: say &quot;Friday&quot; to wake, then your command. Manual:
            type or click a command above.
          </div>
        </div>

        <p
          style={{
            textAlign: "center",
            marginTop: 24,
            fontSize: 10,
            letterSpacing: 3,
            color: THEME.faint,
            fontFamily: "'Courier New', monospace",
            textTransform: "uppercase",
          }}
        >
          voice interface
        </p>
      </div>

      <style>{`
        @keyframes slow-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes breathe { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.4); opacity: 0.6; } }
        @keyframes expand-fade { 0% { transform: scale(1); opacity: 0.3; } 100% { transform: scale(1.15); opacity: 0; } }
        @keyframes bounce-dot { 0%, 80%, 100% { transform: translateY(0); } 40% { transform: translateY(-10px); } }
        input:focus { border-color: ${THEME.ink} !important; outline: none; }
        button:hover { opacity: 0.85; }
      `}</style>
    </div>
  );
}
