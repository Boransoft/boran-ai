type Props = {
  isRecording: boolean;
  onStart: () => void;
  onStop: () => void;
  disabled?: boolean;
};

export default function VoiceRecorder({ isRecording, onStart, onStop, disabled }: Props) {
  return (
    <div className="voice-controls">
      {!isRecording ? (
        <button className="primary" onClick={onStart} disabled={disabled}>
          Start Recording
        </button>
      ) : (
        <button className="danger" onClick={onStop} disabled={disabled}>
          Stop Recording
        </button>
      )}
    </div>
  );
}
