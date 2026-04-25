declare module "react-native-audio-record" {
  type InitOptions = {
    sampleRate?: number;
    channels?: number;
    bitsPerSample?: number;
    wavFile?: string;
    audioSource?: number;
  };

  const AudioRecord: {
    init: (options: InitOptions) => void;
    start: () => Promise<void> | void;
    stop: () => Promise<string>;
  };

  export default AudioRecord;
}
