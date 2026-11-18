"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

interface VisibilityPreviewContextValue {
  previewAsUser: boolean;
  togglePreview: () => void;
}

const VisibilityPreviewContext = createContext<VisibilityPreviewContextValue>({
  previewAsUser: false,
  togglePreview: () => {},
});

export function VisibilityPreviewProvider({ children }: { children: ReactNode }) {
  const [previewAsUser, setPreviewAsUser] = useState(false);
  return (
    <VisibilityPreviewContext.Provider
      value={{ previewAsUser, togglePreview: () => setPreviewAsUser((v) => !v) }}
    >
      {children}
    </VisibilityPreviewContext.Provider>
  );
}

export function useVisibilityPreview() {
  return useContext(VisibilityPreviewContext);
}
