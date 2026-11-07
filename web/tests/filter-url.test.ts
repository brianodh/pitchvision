import { describe, expect, it } from "vitest";
import { parseClassesParam, parseTimeParam, serializeClasses } from "@/lib/filter-url";

describe("?classes= deep links", () => {
  it("parses slugs, raw class names and mixed case, in lane order", () => {
    expect(parseClassesParam("shot")).toEqual(["SHOT"]);
    expect(parseClassesParam("cross,pass")).toEqual(["PASS", "CROSS"]);
    expect(parseClassesParam("HIGH PASS, throw-in")).toEqual(["HIGH PASS", "THROW IN"]);
    expect(parseClassesParam(["shot", "header"])).toEqual(["SHOT", "HEADER"]);
  });

  it("drops unknown slugs, and treats nothing valid as no filter", () => {
    expect(parseClassesParam("corner,shot")).toEqual(["SHOT"]);
    expect(parseClassesParam("corner")).toEqual([]);
    expect(parseClassesParam(undefined)).toEqual([]);
    expect(parseClassesParam("")).toEqual([]);
  });

  it("round-trips, and serialises the same selection to the same URL regardless of click order", () => {
    expect(serializeClasses(["SHOT", "PASS"])).toBe("pass,shot");
    expect(serializeClasses(["PASS", "SHOT"])).toBe("pass,shot");
    expect(parseClassesParam(serializeClasses(["THROW IN", "HIGH PASS"]))).toEqual(["HIGH PASS", "THROW IN"]);
    expect(serializeClasses([])).toBe("");
  });

  it("parses ?t=", () => {
    expect(parseTimeParam("612.5")).toBe(612.5);
    expect(parseTimeParam("-3")).toBeNull();
    expect(parseTimeParam("abc")).toBeNull();
    expect(parseTimeParam(undefined)).toBeNull();
  });
});
