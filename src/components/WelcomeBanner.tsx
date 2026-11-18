"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "github-hr-welcome-dismissed";

export default function WelcomeBanner() {
  const [dismissed, setDismissed] = useState(true); // default hidden to avoid flash

  useEffect(() => {
    setDismissed(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  if (dismissed) return null;

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setDismissed(true);
  };

  return (
    <div className="relative rounded-lg border border-primary/20 bg-primary/5 p-6 mb-8">
      <button
        onClick={handleDismiss}
        className="absolute top-3 right-3 text-muted-foreground hover:text-foreground font-mono text-sm cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center p-2"
        aria-label="Dismiss welcome banner"
      >
        &times;
      </button>

      <h2 className="text-lg font-bold text-foreground mb-3 font-mono">Welcome to GitHub HR</h2>

      <ul className="space-y-2 mb-5 text-sm text-muted-foreground font-mono">
        <li className="flex items-start gap-2">
          <span className="text-primary mt-0.5">1.</span>
          <span>Search GitHub developers by language &amp; location</span>
        </li>
        <li className="flex items-start gap-2">
          <span className="text-primary mt-0.5">2.</span>
          <span>AI scores their code quality across 6 dimensions</span>
        </li>
        <li className="flex items-start gap-2">
          <span className="text-primary mt-0.5">3.</span>
          <span>Get a ranked leaderboard of the best candidates</span>
        </li>
      </ul>

      <Link href="/dashboard/new-task">
        <Button className="font-mono bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer">
          Create your first search _
        </Button>
      </Link>
    </div>
  );
}
