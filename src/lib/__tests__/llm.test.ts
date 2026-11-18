import { describe, expect, it } from "vitest";
import { LlmJsonError, parseJsonReply, stripCodeFence } from "@/lib/llm";

describe("stripCodeFence", () => {
  it("unwraps a ```json fence so the reply parses", () => {
    expect(JSON.parse(stripCodeFence('```json\n{"a": 1}\n```'))).toEqual({ a: 1 });
    expect(JSON.parse(stripCodeFence('```\n{"a": 1}\n```\n'))).toEqual({ a: 1 });
  });
  it("leaves bare JSON alone", () => {
    expect(stripCodeFence(' {"a": 1} ')).toBe('{"a": 1}');
  });
});

describe("parseJsonReply", () => {
  it("parses a fenced or bare reply", () => {
    expect(parseJsonReply('```json\n{"a": 1}\n```')).toEqual({ a: 1 });
    expect(parseJsonReply('{"a": 1}')).toEqual({ a: 1 });
  });
  it("throws LlmJsonError on prose", () => {
    expect(() => parseJsonReply("Sure! Here are the filters.")).toThrow(LlmJsonError);
  });
});
