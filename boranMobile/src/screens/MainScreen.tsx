import React, { useEffect } from "react";

import { ChatScreen } from "./ChatScreen";

type MainScreenProps = {
  token: string;
  onLogout: () => Promise<void>;
};

export function MainScreen({ token, onLogout }: MainScreenProps) {
  const accessToken = token.trim();
  console.log("[main-screen] token:", {
    hasToken: Boolean(accessToken),
    tokenPrefix: accessToken.slice(0, 12),
  });

  useEffect(() => {
    if (!accessToken) {
      void onLogout();
    }
  }, [accessToken, onLogout]);

  if (!accessToken) {
    return null;
  }

  return <ChatScreen token={accessToken} onLogout={onLogout} />;
}
