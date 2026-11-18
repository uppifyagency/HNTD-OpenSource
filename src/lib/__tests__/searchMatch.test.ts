import { describe, it, expect } from "vitest";
import { cacheKey, buildKeywordRegex, matchesKeyword } from "../searchMatch";

describe("cacheKey (UI-16)", () => {
  it("normalizes case", () => {
    expect(cacheKey("React Developer")).toBe(cacheKey("react developer"));
  });

  it("normalizes surrounding and internal whitespace", () => {
    expect(cacheKey("  react   developer ")).toBe("react developer");
  });

  it("keeps distinct queries distinct", () => {
    expect(cacheKey("react developer")).not.toBe(cacheKey("vue developer"));
  });
});

describe("matchesKeyword — word-boundary base cases (BUG-09)", () => {
  it("does not match 'Go' inside 'Google'", () => {
    expect(matchesKeyword("Go", "works at Google")).toBe(false);
  });

  it("matches 'Go' as a standalone token", () => {
    expect(matchesKeyword("Go", "expert in Go and Rust")).toBe(true);
  });

  it("does not match 'C' inside 'CSS'", () => {
    expect(matchesKeyword("C", "CSS wizard")).toBe(false);
  });
});

describe("matchesKeyword — symbol-edged keywords (UI-06)", () => {
  it("matches 'C++' in plain text", () => {
    expect(matchesKeyword("C++", "10 years of C++ experience")).toBe(true);
  });

  it("matches 'C#' in plain text", () => {
    expect(matchesKeyword("C#", "backend in C# and .NET")).toBe(true);
  });

  it("matches '.NET' in plain text", () => {
    expect(matchesKeyword(".NET", "backend in C# and .NET")).toBe(true);
  });

  it("matches '.NET' at start of text", () => {
    expect(matchesKeyword(".NET", ".NET specialist")).toBe(true);
  });

  it("matches 'C++' at end of text", () => {
    expect(matchesKeyword("C++", "loves C++")).toBe(true);
  });

  it("still respects the word-side boundary: 'C++' does not match 'ObjC++ish' prefix word", () => {
    // leading side of "C++" is a word char, so "objc++" must NOT match
    expect(matchesKeyword("C++", "objc++ runtime")).toBe(false);
  });

  it("'C#' does not match inside a longer identifier on the word side", () => {
    expect(matchesKeyword("C#", "ABC# notation")).toBe(false);
  });

  it("is case-insensitive", () => {
    expect(matchesKeyword("c++", "Senior C++ Engineer")).toBe(true);
  });
});

describe("buildKeywordRegex — property: regex special chars never throw and self-match", () => {
  // Property-style sweep: every keyword drawn from this alphabet must
  // (a) compile, (b) match itself embedded between spaces.
  const alphabet = ["a", "B", "9", "+", "#", ".", "(", ")", "[", "]", "*", "?", "^", "$", "{", "}", "|", "\\", "-"];
  const samples: string[] = [];
  for (let len = 1; len <= 3; len++) {
    for (let seed = 0; seed < 200; seed++) {
      let kw = "";
      let x = seed * 2654435761 + len;
      for (let i = 0; i < len; i++) {
        x = (x ^ (x >> 13)) * 0x5bd1e995;
        kw += alphabet[Math.abs(x) % alphabet.length];
      }
      samples.push(kw);
    }
  }

  it("never throws and always matches the keyword embedded as a standalone token", () => {
    for (const kw of samples) {
      const re = buildKeywordRegex(kw);
      expect(re.test(` ${kw} `), `keyword ${JSON.stringify(kw)} must self-match`).toBe(true);
    }
  });

  it("word-char keywords never match as a substring of a longer word", () => {
    for (const kw of samples) {
      if (!/^\w+$/.test(kw)) continue;
      const re = buildKeywordRegex(kw);
      expect(re.test(`x${kw}x`), `keyword ${JSON.stringify(kw)} must not match inside a word`).toBe(false);
    }
  });
});
