/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useEffect, useRef } from "react";
import type { Stats } from "../models/status";
import { API_URL } from "../models/status";

export function useHomeController() {
  const [isPoweredOn, setIsPoweredOn] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isMicOn, setIsMicOn] = useState(true);
  const [isVolumeOn, setIsVolumeOn] = useState(true);
  const [lastCommand, setLastCommand] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
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
          setIsPoweredOn(Boolean(data.isPoweredOn));
          setIsSpeaking(Boolean(data.isSpeaking));
          setIsMicOn(Boolean(data.isMicOn));
          setIsVolumeOn(Boolean(data.isVolumeOn));
          setLastCommand(String(data.lastCommand || ""));
          setStats(data.stats || stats);
        } catch (err) {
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
    let newState = false;

    switch (type) {
      case "power":
        newState = !isPoweredOn;
        setIsPoweredOn(newState);
        break;
      case "mic":
        newState = !isMicOn;
        setIsMicOn(newState);
        break;
      case "volume":
        newState = !isVolumeOn;
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

  const sendCommand = async (text: string) => {
    const trimmedText = text.trim();
    if (!trimmedText) return;
    // Prefer sending commands over the websocket when connected
    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ text: trimmedText }));
        return;
      }

      // Fallback to HTTP POST
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

      try {
        const data = JSON.parse(textBody);
        console.log("Command response:", data);
      } catch (parseErr) {
        console.warn(
          "Expected JSON but received non-JSON response for /command:",
          textBody,
        );
      }
    } catch (err) {
      console.error("Send command failed:", err);
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
    recognition.lang = "en-US";
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

      if (interimTranscript) {
        setTranscript(interimTranscript);
      }

      if (finalTranscript) {
        const trimmedFinal = finalTranscript.trim();
        setTranscript(trimmedFinal);
        latestFinalTranscriptRef.current = trimmedFinal;

        if (sendDelayTimerRef.current) {
          clearTimeout(sendDelayTimerRef.current);
        }

        sendDelayTimerRef.current = setTimeout(() => {
          const commandToSend = latestFinalTranscriptRef.current;
          if (commandToSend) sendCommand(commandToSend);
        }, 3000);

        if (autoStopTimerRef.current) {
          clearTimeout(autoStopTimerRef.current);
        }

        autoStopTimerRef.current = setTimeout(() => {
          if (recognitionRef.current) recognitionRef.current.stop();
        }, 5000);
      }
    };

    recognition.start();
  };

  const handleStopListening = () => {
    if (recognitionRef.current) recognitionRef.current.stop();
    if (sendDelayTimerRef.current) clearTimeout(sendDelayTimerRef.current);
    if (autoStopTimerRef.current) clearTimeout(autoStopTimerRef.current);
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
    stats,
    handleToggle,
    handleSpeak,
    handleListen,
    handleStopListening,
  } as const;
}
