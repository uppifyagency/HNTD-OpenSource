"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { ease } from "@/lib/motion";

export function MobileCTA() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setVisible(window.scrollY > 600);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          exit={{ y: 100 }}
          transition={{ duration: 0.3, ease }}
          className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-white border-t border-border p-3"
          style={{ paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 0.75rem)" }}
        >
          <Link
            href="/sign-up"
            className="block w-full text-center bg-primary text-primary-foreground rounded-full px-6 py-3 font-semibold shadow-lg shadow-primary/25 text-sm active:scale-[0.98] transition-transform"
          >
            Attiva pipeline &rarr;
          </Link>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
