import { useEffect, useState } from "react";

import VoiceRecorder from "../components/VoiceRecorder";
import { useAuthGuard } from "../hooks/useAuthGuard";
import { useRecorder } from "../hooks/useRecorder";
import { chatWithVoice, playAudio } from "../services/voiceService";
import { useAuthStore } from "../store/authStore";
import { useSettingsStore } from "../store/settingsStore";

export default function VoiceChatPage() {
  useAuthGuard();

  const token = useAuthStore((state) => state.token);
  const includeReflectionContext = useSettingsStore((state) => state.includeReflectionContext);
  const preferredAudioFormat = useSettingsStore((state) => state.preferredAudioFormat);

  const { isRecording, audioBlob, error: recorderError, startRecording, stopRecording, clearRecording } =
    useRecorder();

  const [loading, setLoading] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [reply, setReply] = useState("");
  const [audioPlayerUrl, setAudioPlayerUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    return () => {
      if (audioPlayerUrl) {
        URL.revokeObjectURL(audioPlayerUrl);
      }
    };
  }, [audioPlayerUrl]);

  async function sendRecording() {
    if (!token || !audioBlob) return;

    setLoading(true);
    setError("");

    try {
      const ext = audioBlob.type.includes("webm") ? "webm" : "wav";
      const file = new File([audioBlob], `voice-input.${ext}`, {
        type: audioBlob.type || "audio/webm",
      });

      const response = await chatWithVoice({
        token,
        file,
        language: "tr",
        includeReflectionContext,
        audioFormat: preferredAudioFormat,
      });

      setTranscript(response.transcript);
      setReply(response.reply);

      if (audioPlayerUrl) {
        URL.revokeObjectURL(audioPlayerUrl);
      }
      const blobUrl = await playAudio({ token, url: response.audio_url });
      setAudioPlayerUrl(blobUrl);
      clearRecording();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-content">
      <VoiceRecorder isRecording={isRecording} onStart={startRecording} onStop={stopRecording} disabled={loading} />

      {audioBlob ? (
        <button className="primary" onClick={sendRecording} disabled={loading}>
          {loading ? "Processing..." : "Send Voice Message"}
        </button>
      ) : null}

      {recorderError ? <p className="error-text">{recorderError}</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      <section className="card">
        <h3>Transcript</h3>
        <p>{transcript || "No transcript yet."}</p>
      </section>

      <section className="card">
        <h3>AI Reply</h3>
        <p>{reply || "No reply yet."}</p>
      </section>

      <section className="card">
        <h3>Audio Reply</h3>
        {audioPlayerUrl ? (
          <audio controls src={audioPlayerUrl} className="audio-player" />
        ) : (
          <p>No audio generated yet.</p>
        )}
      </section>
    </section>
  );
}
