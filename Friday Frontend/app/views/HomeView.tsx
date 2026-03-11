/* eslint-disable react-hooks/rules-of-hooks */
"use client";

import React, { useEffect, useState } from "react";
import { Mic, MicOff, Volume2, VolumeX, Power } from "lucide-react";
import type { Stats } from "../models/status";

type Controller = Readonly<{
  isPoweredOn: boolean;
  isSpeaking: boolean;
  isMicOn: boolean;
  isVolumeOn: boolean;
  lastCommand: string;
  isListening: boolean;
  transcript: string;
  stats: Stats;
  handleToggle: (t: "power" | "mic" | "volume") => void;
  handleSpeak: () => void;
  handleListen: () => void;
  handleStopListening: () => void;
}>;

/* ===============================
   MINIMAL THEME
================================ */
const THEME = {
  ink: "#0f0f0f",
  muted: "#aaa",
  faint: "#e0d0d8",
  border: "#eddde6",
  bg: "#fdf8fb",
  accent: "#c8648a",
  pink: "#d4728f",
  pinkLight: "#f5e6ed",
  pinkFaint: "rgba(212,114,143,0.15)",
};

/* ===============================
   CORE INDICATOR
================================ */
function CoreIndicator({
  active,
  speaking,
  listening,
}: {
  active: boolean;
  speaking: boolean;
  listening: boolean;
}) {
  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: 160, height: 160 }}
    >
      {/* Outer ring */}
      <div
        className="absolute rounded-full"
        style={{
          width: 160,
          height: 160,
          border: `1px solid ${active ? THEME.ink : THEME.border}`,
          transition: "border-color 0.6s ease",
        }}
      />

      {/* Mid ring - listening pulse */}
      <div
        className="absolute rounded-full"
        style={{
          width: 120,
          height: 120,
          border: `1px solid ${active ? THEME.faint : "transparent"}`,
          transition: "border-color 0.6s ease",
          animation:
            listening && active ? "slow-spin 12s linear infinite" : "none",
        }}
      />

      {/* Core dot */}
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: active ? (speaking ? THEME.ink : THEME.ink) : THEME.faint,
          transition: "all 0.5s ease",
          animation:
            listening && active ? "breathe 2s ease-in-out infinite" : "none",
        }}
      />

      {/* Listening indicator ring */}
      {listening && active && (
        <div
          className="absolute rounded-full"
          style={{
            width: 180,
            height: 180,
            border: `1px solid ${THEME.faint}`,
            animation: "expand-fade 1.8s ease-out infinite",
          }}
        />
      )}
    </div>
  );
}

/* ===============================
   CONTROL BUTTON
================================ */
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

/* ===============================
   HOME VIEW
================================ */
export default function HomeView(props: { controller: Controller }) {
  const c = props.controller;
  const [time, setTime] = useState("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

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
      <div style={{ width: "100%", maxWidth: 340 }}>
        {/* Header */}
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

        {/* Main panel */}
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
          {/* Status line */}
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
              {c.isPoweredOn ? "online" : "offline"}
            </span>
          </div>

          {/* Core */}
          <CoreIndicator
            active={c.isPoweredOn}
            speaking={c.isSpeaking}
            listening={c.isListening}
          />

          {/* Controls */}
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

          {/* Activate button */}
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
        </div>

        {/* Footer label */}
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
        @keyframes slow-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes breathe {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.4); opacity: 0.6; }
        }
        @keyframes expand-fade {
          0% { transform: scale(1); opacity: 0.3; }
          100% { transform: scale(1.15); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
