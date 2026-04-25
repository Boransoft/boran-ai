import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import ReactNativeBlobUtil from "react-native-blob-util";
import Sound from "react-native-sound";

import { downloadAudioToCache } from "../services/voiceService";
import { theme } from "../utils/theme";

type AudioPlayerProps = {
  token: string;
  audioUrl: string;
};

Sound.setCategory("Playback");

export function AudioPlayer({ token, audioUrl }: AudioPlayerProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const soundRef = useRef<Sound | null>(null);
  const localPathRef = useRef<string | null>(null);

  const release = () => {
    if (soundRef.current) {
      soundRef.current.release();
      soundRef.current = null;
    }
    setIsPlaying(false);
  };

  const cleanupFile = async () => {
    if (!localPathRef.current) {
      return;
    }
    try {
      await ReactNativeBlobUtil.fs.unlink(localPathRef.current);
    } catch {
      // no-op
    } finally {
      localPathRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      release();
      void cleanupFile();
    };
  }, []);

  const handlePress = async () => {
    setErrorText(null);
    if (isPlaying) {
      release();
      await cleanupFile();
      return;
    }

    try {
      setIsLoading(true);
      const path = await downloadAudioToCache({ token, audioUrl });
      localPathRef.current = path;

      const sound = new Sound(path, "", (error) => {
        if (error) {
          setErrorText("Ses dosyasi acilamadi.");
          setIsLoading(false);
          return;
        }
        soundRef.current = sound;
        setIsLoading(false);
        setIsPlaying(true);
        sound.play(async (ok) => {
          release();
          await cleanupFile();
          if (!ok) {
            setErrorText("Ses oynatma tamamlanamadi.");
          }
        });
      });
    } catch {
      setErrorText("Ses dosyasi indirilemedi.");
      setIsLoading(false);
    }
  };

  return (
    <View style={styles.wrap}>
      <Pressable style={styles.button} onPress={handlePress} disabled={isLoading}>
        {isLoading ? (
          <ActivityIndicator size="small" color={theme.colors.text} />
        ) : (
          <Text style={styles.label}>{isPlaying ? "DURDUR" : "SESI OYNAT"}</Text>
        )}
      </Pressable>
      {errorText ? <Text style={styles.error}>{errorText}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 8,
  },
  button: {
    minHeight: 34,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 10,
  },
  label: {
    color: theme.colors.text,
    fontWeight: "700",
    fontSize: 12,
  },
  error: {
    marginTop: 6,
    color: theme.colors.danger,
    fontSize: 12,
  },
});
