import { beforeAll, describe, expect, it, vi } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// library.server.ts imports "server-only", which throws outside a Next server build. Stub it for unit tests.
vi.mock("server-only", () => ({}));

import { matchDir, resolveInMatch } from "@/lib/library.server";

beforeAll(() => {
  process.env.PV_DATA_DIR = fs.mkdtempSync(path.join(os.tmpdir(), "pv-data-"));
});

describe("resolveInMatch: stays inside the match folder", () => {
  it("resolves a normal nested file inside the match folder", () => {
    expect(resolveInMatch("m1", "thumbs/a.jpg")).toBe(path.join(matchDir("m1"), "thumbs", "a.jpg"));
  });

  it("refuses ../ traversal, however it is nested", () => {
    expect(resolveInMatch("m1", "../other/match.json")).toBeNull();
    expect(resolveInMatch("m1", "../../../../etc/passwd")).toBeNull();
    expect(resolveInMatch("m1", "thumbs/../../escape.txt")).toBeNull();
  });

  it("refuses absolute paths", () => {
    expect(resolveInMatch("m1", "/etc/passwd")).toBeNull();
  });

  it("refuses the sibling-prefix trick (m1 vs m10)", () => {
    expect(resolveInMatch("m1", "../m10/match.json")).toBeNull();
  });

  it("refuses the folder itself", () => {
    expect(resolveInMatch("m1", "")).toBeNull();
    expect(resolveInMatch("m1", ".")).toBeNull();
  });

  it("allows a dotted-looking name that is still inside the folder", () => {
    expect(resolveInMatch("m1", "thumbs/..hidden.jpg")).not.toBeNull();
  });

  it("throws on an invalid match id instead of building a path", () => {
    expect(() => resolveInMatch("../x", "a.json")).toThrow(/invalid match id/);
    expect(() => resolveInMatch("a/b", "a.json")).toThrow(/invalid match id/);
  });
});
