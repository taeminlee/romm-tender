import { describe, expect, it } from "vitest";
import { isNewer, forkVersionKey } from "./ForkUpdateBanner";
describe("fork version", () => {
  it("compares msu numbers", () => {
    expect(isNewer("0.33.1-msu5", "0.33.1-msu4")).toBe(true);
    expect(isNewer("0.33.1-msu10", "0.33.1-msu9")).toBe(true);
    expect(isNewer("0.33.1-msu4", "0.33.1-msu4")).toBe(false);
    expect(isNewer("0.33.1-msu3", "0.33.1-msu4")).toBe(false);
    expect(isNewer("0.34.0", "0.33.1-msu9")).toBe(true);
    expect(forkVersionKey("dev")).toBe(null);
  });
});
