"use client";

import { useState, useRef, useCallback, useMemo } from "react";
import {
  GITHUB_LANGUAGE_MAP,
  splitInput,
  classifyTerm,
  getSuggestions,
  type LanguageMapEntry,
} from "@/lib/github-language-map";

export interface TagItem {
  term: string;
  label: string;
  isLanguage: boolean;
  entry: LanguageMapEntry | null;
}

interface SmartTagInputProps {
  tags: TagItem[];
  onChange: (tags: TagItem[]) => void;
  placeholder?: string;
}

/** All unique entries for autocomplete, deduped by label */
const AUTOCOMPLETE_ENTRIES = (() => {
  const seen = new Set<string>();
  const entries: Array<{ key: string; entry: LanguageMapEntry }> = [];
  for (const [key, entry] of Object.entries(GITHUB_LANGUAGE_MAP)) {
    if (!seen.has(entry.label)) {
      seen.add(entry.label);
      entries.push({ key, entry });
    }
  }
  return entries.sort((a, b) => a.entry.label.localeCompare(b.entry.label));
})();

export default function SmartTagInput({
  tags,
  onChange,
  placeholder = "python, docker, react, kubernetes...",
}: SmartTagInputProps) {
  const [input, setInput] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const existingLabels = useMemo(
    () => new Set(tags.map((t) => t.label.toLowerCase())),
    [tags]
  );

  const filteredEntries = useMemo(() => {
    if (!input.trim()) return AUTOCOMPLETE_ENTRIES.slice(0, 12);
    const q = input.toLowerCase().trim();
    return AUTOCOMPLETE_ENTRIES.filter(
      (e) =>
        (e.key.includes(q) || e.entry.label.toLowerCase().includes(q)) &&
        !existingLabels.has(e.entry.label.toLowerCase())
    ).slice(0, 8);
  }, [input, existingLabels]);

  const suggestions = useMemo(() => {
    const classified = tags.map((t) => ({ term: t.term, entry: t.entry }));
    return getSuggestions(classified).filter(
      (s) => !existingLabels.has(s.toLowerCase())
    );
  }, [tags, existingLabels]);

  const addTag = useCallback(
    (term: string) => {
      const { entry, isLanguage } = classifyTerm(term);
      const label = entry?.label ?? term;
      if (existingLabels.has(label.toLowerCase())) return;
      onChange([...tags, { term, label, isLanguage, entry }]);
    },
    [tags, onChange, existingLabels]
  );

  const removeTag = useCallback(
    (index: number) => {
      onChange(tags.filter((_, i) => i !== index));
    },
    [tags, onChange]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const parts = splitInput(input);
      for (const part of parts) {
        if (part) addTag(part);
      }
      setInput("");
      setShowDropdown(false);
    } else if (e.key === "Backspace" && input === "" && tags.length > 0) {
      removeTag(tags.length - 1);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  };

  const handleSelect = (key: string, entry: LanguageMapEntry) => {
    if (!existingLabels.has(entry.label.toLowerCase())) {
      onChange([
        ...tags,
        {
          term: key,
          label: entry.label,
          isLanguage: entry.linguistName != null,
          entry,
        },
      ]);
    }
    setInput("");
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const handleSuggestionClick = (label: string) => {
    const key = label.toLowerCase();
    addTag(key);
    inputRef.current?.focus();
  };

  return (
    <div className="space-y-2">
      {/* Tag input container */}
      <div
        className="flex flex-wrap gap-1.5 min-h-[44px] p-2 rounded-md border border-border bg-card cursor-text focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20"
        onClick={() => inputRef.current?.focus()}
      >
        {tags.map((tag, i) => (
          <span
            key={`${tag.label}-${i}`}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-xs ${
              tag.isLanguage
                ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                : "bg-secondary text-secondary-foreground border border-border"
            }`}
          >
            {tag.label}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeTag(i);
              }}
              className="ml-0.5 hover:opacity-70 cursor-pointer"
            >
              x
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => {
            // Delay to allow click on dropdown
            setTimeout(() => setShowDropdown(false), 200);
          }}
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[120px] outline-none bg-transparent font-mono text-sm text-foreground placeholder:text-muted-foreground/50"
        />
      </div>

      {/* Autocomplete dropdown */}
      {showDropdown && filteredEntries.length > 0 && (
        <div className="border border-border rounded-md bg-white shadow-lg max-h-[200px] overflow-y-auto">
          {filteredEntries.map(({ key, entry }) => (
            <button
              key={key}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleSelect(key, entry)}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-muted/50 font-mono text-sm cursor-pointer"
            >
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  entry.linguistName ? "bg-emerald-500" : "bg-muted-foreground"
                }`}
              />
              <span className="text-foreground">{entry.label}</span>
              <span className="text-muted-foreground text-xs ml-auto">
                {entry.category}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-xs text-muted-foreground">
            Also search:
          </span>
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => handleSuggestionClick(s)}
              className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded font-mono text-xs bg-muted text-muted-foreground border border-dashed border-border hover:bg-muted/80 hover:text-foreground cursor-pointer"
            >
              + {s}
            </button>
          ))}
        </div>
      )}

      {/* Legend */}
      {tags.length > 0 && (
        <div className="flex gap-3 font-mono text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
            language
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-muted-foreground" />
            keyword
          </span>
        </div>
      )}
    </div>
  );
}
