/** Shared easing curve for framer-motion animations across landing page components. */
export const ease = [0.4, 0, 0.2, 1] as const;

export const fadeUp = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.6, ease },
};

export const stagger = (delay: number) => ({
  ...fadeUp,
  transition: { duration: 0.6, delay, ease },
});
