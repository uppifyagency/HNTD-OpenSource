"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ease } from "@/lib/motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

const demos = [
  {
    query: "frontend engineer con esperienza React e design system",
    profile: {
      initial: "A",
      name: "alessrog",
      handle: "@alessrog",
      match: 96,
      repo: "design-system-kit",
      desc: "Libreria UI component accessibile con 40+ componenti React, Storybook e test e2e integrati",
      stars: 1247,
      forks: 89,
      tags: ["React", "TypeScript", "Storybook", "Tailwind"],
    },
  },
  {
    query: "backend engineer Go microservizi ad alta scalabilità",
    profile: {
      initial: "S",
      name: "saradev",
      handle: "@saradev",
      match: 93,
      repo: "go-event-broker",
      desc: "Message broker event-driven in Go con supporto gRPC, retry automatico e observability nativa",
      stars: 892,
      forks: 134,
      tags: ["Go", "gRPC", "Kubernetes", "Redis"],
    },
  },
  {
    query: "ML engineer Python pipeline dati real-time",
    profile: {
      initial: "M",
      name: "marcml",
      handle: "@marcml",
      match: 91,
      repo: "stream-ml-pipeline",
      desc: "Pipeline ML real-time con Apache Kafka, feature store custom e deploy automatico su Kubernetes",
      stars: 2103,
      forks: 267,
      tags: ["Python", "PyTorch", "Kafka", "Docker"],
    },
  },
  {
    query: "DevOps engineer Terraform infrastruttura cloud AWS",
    profile: {
      initial: "J",
      name: "jcloud",
      handle: "@jcloud",
      match: 89,
      repo: "terraform-aws-modules",
      desc: "Moduli Terraform production-ready per infrastruttura AWS: ECS, RDS, VPC con monitoring integrato",
      stars: 1580,
      forks: 203,
      tags: ["Terraform", "AWS", "Docker", "Prometheus"],
    },
  },
];

export function SearchDemo() {
  const [current, setCurrent] = useState(0);
  const [typedQuery, setTypedQuery] = useState("");
  const [showResult, setShowResult] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const demo = demos[current];
    let charIndex = 0;
    setTypedQuery("");
    setShowResult(false);

    const addTimer = (id: ReturnType<typeof setTimeout>) => {
      timersRef.current.push(id);
    };

    const typeInterval = setInterval(() => {
      if (charIndex < demo.query.length) {
        setTypedQuery(demo.query.slice(0, charIndex + 1));
        charIndex++;
      } else {
        clearInterval(typeInterval);
        addTimer(setTimeout(() => setShowResult(true), 400));
        addTimer(
          setTimeout(() => {
            setShowResult(false);
            addTimer(
              setTimeout(
                () => setCurrent((prev) => (prev + 1) % demos.length),
                600
              )
            );
          }, 5000)
        );
      }
    }, 35);

    return () => {
      clearInterval(typeInterval);
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    };
  }, [current]);

  const profile = demos[current].profile;

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      {/* Search bar */}
      <Card className="py-0 shadow-lg shadow-foreground/[0.04]">
        <CardContent className="flex items-center gap-3 px-5 py-3.5">
          <svg
            className="w-4 h-4 text-muted-foreground shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <span className="font-mono text-sm text-foreground flex-1 text-left min-w-0 truncate">
            {typedQuery}
            <span className="inline-block w-[2px] h-4 bg-primary cursor-blink ml-0.5 align-middle rounded-full" />
          </span>
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0 shadow-md shadow-primary/20">
            <svg
              className="w-4 h-4 text-primary-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M14 5l7 7m0 0l-7 7m7-7H3"
              />
            </svg>
          </div>
        </CardContent>
      </Card>

      {/* Result card */}
      <AnimatePresence>
        {showResult && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            transition={{ duration: 0.35, ease }}
            className="mt-3"
          >
            <Card className="shadow-xl shadow-foreground/[0.06] py-0">
              <CardContent className="p-5">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center font-mono text-primary font-bold text-sm shrink-0 ring-1 ring-primary/20">
                    {profile.initial}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-foreground text-sm">
                        {profile.name}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {profile.handle}
                      </span>
                      <Badge variant="secondary" className="ml-auto font-mono text-xs text-primary bg-primary/10 rounded-full font-semibold">
                        {profile.match}% match
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <svg
                        className="w-3.5 h-3.5 text-primary"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                      </svg>
                      <span className="font-mono font-semibold text-primary">
                        {profile.repo}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                      {profile.desc}
                    </p>
                    <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground font-mono">
                      <span>&#9733; {profile.stars.toLocaleString()}</span>
                      <span>&#9741; {profile.forks}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {profile.tags.map((tag) => (
                        <Badge
                          key={tag}
                          variant="secondary"
                          className="font-mono text-[10px] rounded-md"
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
