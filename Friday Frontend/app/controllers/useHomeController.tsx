/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useEffect, useRef } from "react";
import type { Stats } from "../models/status";
import { API_URL } from "../models/status";

export type AlertItem = {
  id: string;
  level: string;
  title: string;
  message?: string;
  createdAt?: string;
  expiresAt?: string;
  meta?: Record<string, unknown>;
};

export type ReminderItem = {
  id: string;
  title: string;
  dueAt: string;
  createdAt?: string;
  repeat?: string;
  done?: boolean;
};

export type VisionStatus = {
  airMouse: boolean;
  signLauncher: boolean;
};

export function useHomeController() {
  const [isPoweredOn, setIsPoweredOn] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isMicOn, setIsMicOn] = useState(true);
  const [isVolumeOn, setIsVolumeOn] = useState(true);
  const [lastCommand, setLastCommand] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [vision, setVision] = useState<VisionStatus>({
    airMouse: false,
    signLauncher: false,
  });
  const [stats, setStats] = useState<Stats>({
    battery: 87,
    temperature: 42,
    cpu: 34,
    connectivity: "Strong",
    uptime: "0h 0m",
  });

  const recognitionRef = useRef<any>(null);
  const sendDelayTimerRef = useRef<any>(null);
  const autoStopTimerRef = useRef<any>(null);
  const latestFinalTranscriptRef = useRef<string>("");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    try {
      const apiUrl = new URL(API_URL);
      const wsProtocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProtocol}//${apiUrl.host}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => console.log("WebSocket connected", wsUrl);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setIsSpeaking(Boolean(data.isSpeaking));
          setLastCommand(String(data.lastCommand || ""));
          setStats((prev) => data.stats || prev);
          if (Array.isArray(data.alerts)) setAlerts(data.alerts);
          if (Array.isArray(data.reminders)) setReminders(data.reminders);
          if (data.vision && typeof data.vision === "object") {
            setVision({
              airMouse: Boolean((data.vision as any).airMouse),
              signLauncher: Boolean((data.vision as any).signLauncher),
            });
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        wsRef.current = null;
      };

      ws.onerror = (e) => console.warn("WebSocket error", e);

      return () => {
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
      };
    } catch (err) {
      console.warn("Failed to open WebSocket", err);
    }
  }, []);

  const handleToggle = async (type: "power" | "mic" | "volume") => {
    let newState: boolean;
    switch (type) {
      case "power":
        newState = !isPoweredOn;
        break;
      case "mic":
        newState = !isMicOn;
        break;
      case "volume":
        newState = !isVolumeOn;
        break;
      default:
        return;
    }
    switch (type) {
      case "power":
        setIsPoweredOn(newState);
        break;
      case "mic":
        setIsMicOn(newState);
        break;
      case "volume":
        setIsVolumeOn(newState);
        break;
    }
    try {
      await fetch(`${API_URL}/${type}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: newState }),
      });
    } catch (err) {
      console.error(`Failed to toggle ${type}:`, err);
    }
  };

  const handleSpeak = async () => {
    if (!isPoweredOn || !isVolumeOn) return;
    try {
      await fetch(`${API_URL}/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: "Hello sir, how can I help you?" }),
      });
    } catch (err) {
      console.error("Failed to speak:", err);
    }
  };

  const toggleAirMouse = async () => {
    try {
      const endpoint = vision.airMouse ? "airmouse/stop" : "airmouse/start";
      await fetch(`${API_URL}/${endpoint}`, { method: "POST" });
    } catch (err) {
      console.error("AirMouse toggle failed:", err);
    }
  };

  const toggleSignLauncher = async () => {
    try {
      const endpoint = vision.signLauncher
        ? "signlauncher/stop"
        : "signlauncher/start";
      await fetch(`${API_URL}/${endpoint}`, { method: "POST" });
    } catch (err) {
      console.error("SignLauncher toggle failed:", err);
    }
  };

  // ─────────────────────────────────────────────
  // Send Command — WebSocket or HTTP fallback
  // ─────────────────────────────────────────────
  const sendCommand = async (text: string) => {
    const trimmedText = text.trim();
    if (!trimmedText) return;
    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ text: trimmedText }));
        return;
      }
      const response = await fetch(`${API_URL}/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmedText }),
      });
      const textBody = await response.text();
      if (!response.ok) {
        console.warn(
          "Command POST returned non-OK status",
          response.status,
          textBody,
        );
      }
    } catch (err) {
      console.error("Send command failed:", err);
    }
  };

  // ─────────────────────────────────────────────
  // Add Reminder Manually
  // ─────────────────────────────────────────────
  const addReminderManual = async (title: string, dueAt: string) => {
    try {
      await fetch(`${API_URL}/reminders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, dueAt, repeat: "none" }),
      });
    } catch (err) {
      console.error("Add reminder failed:", err);
    }
  };

  // ─────────────────────────────────────────────
  // Delete Reminder
  // ─────────────────────────────────────────────
  const deleteReminder = async (id: string) => {
    try {
      await fetch(`${API_URL}/reminders/${id}`, { method: "DELETE" });
    } catch (err) {
      console.error("Delete reminder failed:", err);
    }
  };

  const handleListen = () => {
    if (!isPoweredOn || !isMicOn) return;

    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Use Chrome browser (speech recognition not supported)");
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-PH";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript("");
      latestFinalTranscriptRef.current = "";
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognition.onerror = (event: any) => {
      console.error("Speech error:", event.error);
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      if (interimTranscript) setTranscript(interimTranscript);

      if (finalTranscript) {
        const trimmedFinal = finalTranscript.trim();
        setTranscript(trimmedFinal);
        latestFinalTranscriptRef.current = trimmedFinal;

        if (sendDelayTimerRef.current) clearTimeout(sendDelayTimerRef.current);
        sendDelayTimerRef.current = setTimeout(() => {
          const commandToSend = latestFinalTranscriptRef.current;
          if (commandToSend) sendCommand(commandToSend);
        }, 1500);

        if (autoStopTimerRef.current) clearTimeout(autoStopTimerRef.current);
        autoStopTimerRef.current = setTimeout(() => {
          if (recognitionRef.current) recognitionRef.current.stop();
        }, 6000);
      }
    };

    recognition.start();
  };

  const handleStopListening = () => {
    if (recognitionRef.current) recognitionRef.current.stop();
    if (sendDelayTimerRef.current) clearTimeout(sendDelayTimerRef.current);
    if (autoStopTimerRef.current) clearTimeout(autoStopTimerRef.current);
  };

  const clearTranscript = () => {
    setTranscript("");
    latestFinalTranscriptRef.current = "";
  };

  useEffect(() => {
    return () => {
      if (recognitionRef.current) recognitionRef.current.stop();
      if (sendDelayTimerRef.current) clearTimeout(sendDelayTimerRef.current);
      if (autoStopTimerRef.current) clearTimeout(autoStopTimerRef.current);
    };
  }, []);

  return {
    isPoweredOn,
    isSpeaking,
    isMicOn,
    isVolumeOn,
    lastCommand,
    isListening,
    transcript,
    alerts,
    reminders,
    vision,
    stats,
    handleToggle,
    handleSpeak,
    handleListen,
    handleStopListening,
    toggleAirMouse,
    toggleSignLauncher,
    sendCommand,
    addReminderManual,
    deleteReminder,
    clearTranscript,
  } as const;
}
