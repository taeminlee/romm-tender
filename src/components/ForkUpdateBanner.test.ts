import { describe, expect, it, vi } from "vitest";
import { isNewer, forkVersionKey, fetchNewest, installRelease, INSTALL_TYPE_REINSTALL } from "./ForkUpdateBanner";
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

describe("fork release lookup and install (msu9)", () => {
  const releases = [
    {
      tag_name: "tender-v0.33.1-msu9",
      draft: false,
      prerelease: false,
      assets: [{ name: "Tender.zip", browser_download_url: "https://x/9.zip", digest: "sha256:abc" }],
    },
    {
      tag_name: "tender-v0.33.1-msu10",
      draft: true,
      prerelease: false,
      assets: [{ name: "Tender.zip", browser_download_url: "https://x/10.zip", digest: "sha256:def" }],
    },
  ];

  it("force skips the cache and picks the newest published release", async () => {
    localStorage.setItem("tender-fork-update", JSON.stringify({ at: Date.now(), rel: null }));
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => releases }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await fetchNewest()).toBe(null);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(await fetchNewest(true)).toEqual({ version: "0.33.1-msu9", url: "https://x/9.zip", sha256: "abc" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });

  it("hands the zip to Decky's installer with the given install type", async () => {
    const call = vi.fn(async () => undefined);
    (globalThis as unknown as { DeckyBackend?: unknown }).DeckyBackend = { call };
    const ok = await installRelease(
      { version: "0.33.1-msu9", url: "https://x/9.zip", sha256: "abc" },
      INSTALL_TYPE_REINSTALL,
    );
    expect(ok).toBe(true);
    expect(call).toHaveBeenCalledWith("utilities/install_plugin", "https://x/9.zip", "Tender", "0.33.1-msu9", "abc", 1);
    delete (globalThis as unknown as { DeckyBackend?: unknown }).DeckyBackend;
    expect(await installRelease({ version: "v", url: "u", sha256: "" }, INSTALL_TYPE_REINSTALL)).toBe(false);
  });
});
