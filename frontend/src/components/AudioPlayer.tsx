import { useEffect, useRef } from "react";

type AudioPlayerProps = {
  src: string;
  autoPlay?: boolean;
  onPlay?: () => void;
  onEnded?: () => void;
  onError?: () => void;
};

export default function AudioPlayer({ src, autoPlay, onPlay, onEnded, onError }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!autoPlay || !audioRef.current) {
      return;
    }

    audioRef.current
      .play()
      .then(() => {
        onPlay?.();
      })
      .catch(() => {
        onError?.();
      });
  }, [autoPlay, onError, onPlay, src]);

  return (
    <audio
      ref={audioRef}
      controls
      preload="metadata"
      src={src}
      className="mt-2 w-full"
      onPlay={onPlay}
      onEnded={onEnded}
      onError={onError}
    />
  );
}
