(() => {
  const apiBaseInput = document.getElementById("apiBase");
  const tokenInput = document.getElementById("token");
  const languageInput = document.getElementById("language");
  const startBtn = document.getElementById("startBtn");
  const stopBtn = document.getElementById("stopBtn");
  const sendBtn = document.getElementById("sendBtn");
  const statusEl = document.getElementById("status");
  const errorEl = document.getElementById("error");
  const formatInfoEl = document.getElementById("formatInfo");
  const transcriptEl = document.getElementById("transcript");
  const replyEl = document.getElementById("reply");
  const player = document.getElementById("player");

  const state = {
    mediaRecorder: null,
    mediaStream: null,
    chunks: [],
    blob: null,
    mimeType: "",
    playbackUrl: "",
  };

  apiBaseInput.value = window.location.origin;

  function setStatus(value) {
    statusEl.textContent = value;
  }

  function setError(message) {
    errorEl.textContent = message || "";
  }

  function pickRecorderMimeType() {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/wav",
    ];
    for (const mime of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(mime)) {
        return mime;
      }
    }
    return "";
  }

  function cleanupPlaybackUrl() {
    if (state.playbackUrl) {
      URL.revokeObjectURL(state.playbackUrl);
      state.playbackUrl = "";
    }
  }

  async function startRecording() {
    setError("");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError("getUserMedia not supported in this browser.");
      return;
    }

    if (!window.MediaRecorder) {
      setError("MediaRecorder not supported in this browser.");
      return;
    }

    const mimeType = pickRecorderMimeType();
    if (!mimeType) {
      setError("No supported MediaRecorder audio mime type found.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType });

      state.mediaStream = stream;
      state.mediaRecorder = recorder;
      state.mimeType = mimeType;
      state.chunks = [];
      state.blob = null;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          state.chunks.push(event.data);
        }
      };

      recorder.onstop = () => {
        state.blob = new Blob(state.chunks, { type: recorder.mimeType || mimeType });
        setStatus("idle");
        sendBtn.disabled = !state.blob;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        if (state.mediaStream) {
          state.mediaStream.getTracks().forEach((track) => track.stop());
        }
      };

      recorder.start();
      formatInfoEl.textContent = `Recorder format: ${mimeType}`;
      setStatus("recording");
      sendBtn.disabled = true;
      startBtn.disabled = true;
      stopBtn.disabled = false;
    } catch (error) {
      setError(error instanceof Error ? error.message : "Microphone access failed.");
    }
  }

  function stopRecording() {
    if (!state.mediaRecorder) {
      return;
    }

    if (state.mediaRecorder.state !== "inactive") {
      state.mediaRecorder.stop();
    }
  }

  function extFromMime(mime) {
    const normalized = (mime || "").toLowerCase();
    if (normalized.includes("webm")) return "webm";
    if (normalized.includes("wav")) return "wav";
    if (normalized.includes("mp4") || normalized.includes("m4a")) return "m4a";
    if (normalized.includes("ogg") || normalized.includes("opus")) return "ogg";
    return "webm";
  }

  async function sendVoiceChat() {
    setError("");
    if (!state.blob) {
      setError("No recorded audio found.");
      return;
    }

    const token = tokenInput.value.trim();
    if (!token) {
      setError("Bearer token is required.");
      return;
    }

    const apiBase = apiBaseInput.value.trim() || window.location.origin;
    const language = languageInput.value.trim();
    const extension = extFromMime(state.blob.type);
    const file = new File([state.blob], `voice-test.${extension}`, {
      type: state.blob.type || "audio/webm",
    });

    const form = new FormData();
    form.append("audio", file);
    if (language) {
      form.append("language", language);
    }
    form.append("include_reflection_context", "true");
    form.append("audio_format", "mp3");

    setStatus("processing");
    sendBtn.disabled = true;

    try {
      const response = await fetch(`${apiBase}/voice/chat`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: form,
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `${response.status} ${response.statusText}`);
      }

      transcriptEl.textContent = payload.transcript || "-";
      replyEl.textContent = payload.reply || "-";

      if (!payload.audio_url) {
        throw new Error("audio_url missing in /voice/chat response");
      }

      cleanupPlaybackUrl();
      const audioResponse = await fetch(`${apiBase}${payload.audio_url}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!audioResponse.ok) {
        throw new Error(`Audio fetch failed: ${audioResponse.status}`);
      }

      const audioBlob = await audioResponse.blob();
      state.playbackUrl = URL.createObjectURL(audioBlob);
      player.src = state.playbackUrl;
      setStatus("playing");
      try {
        await player.play();
      } catch {
        // Autoplay can fail on mobile without gesture; controls remain available.
      }
      setStatus("idle");
    } catch (error) {
      setStatus("idle");
      setError(error instanceof Error ? error.message : "Voice chat failed");
    } finally {
      sendBtn.disabled = false;
    }
  }

  startBtn.addEventListener("click", startRecording);
  stopBtn.addEventListener("click", stopRecording);
  sendBtn.addEventListener("click", sendVoiceChat);

  player.addEventListener("playing", () => setStatus("playing"));
  player.addEventListener("ended", () => setStatus("idle"));
  player.addEventListener("pause", () => setStatus("idle"));

  setStatus("idle");
})();
