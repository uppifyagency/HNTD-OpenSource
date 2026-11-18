"use client";

import { useQuery } from "convex/react";
import { useSessionUser } from "@/lib/session";
import { api } from "../../convex/_generated/api";
import { isAdmin } from "@/lib/admin";
import { useVisibilityPreview } from "@/contexts/VisibilityPreviewContext";

/**
 * Returns whether a UI element should be visible.
 * Checks the element ID and all ancestor IDs against frontendConfig overrides.
 * Admin users always see everything — unless preview mode is active.
 */
export function useVisibility(id: string): boolean {
  const user = useSessionUser();
  const { previewAsUser } = useVisibilityPreview();
  const config = useQuery(api.frontendConfig.getConfig, user ? undefined : "skip");

  // Admin bypass — admins see everything, unless previewing as user
  if (!previewAsUser && isAdmin(user?.email)) {
    return true;
  }

  // Config not loaded yet or no config document — default visible
  if (config === undefined || config === null) {
    return true;
  }

  const { overrides } = config;

  // Check the ID itself and all ancestors
  // e.g. "devProfile.scoreBreakdown.codeQuality" checks:
  //   "devProfile", "devProfile.scoreBreakdown", "devProfile.scoreBreakdown.codeQuality"
  const parts = id.split(".");
  for (let i = 1; i <= parts.length; i++) {
    const ancestorId = parts.slice(0, i).join(".");
    if (overrides[ancestorId] === false) {
      return false;
    }
  }

  return true;
}
