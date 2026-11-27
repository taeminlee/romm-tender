// Fork addition (0.33.1-msu5): update this unofficial build from inside Tender.
//
// Plugins installed from a URL get no updates from the Decky store, so each
// fork release meant typing its URL again. This banner asks GitHub for the
// newest fork release (taeminlee/romm-tender, tags `tender-v0.33.1-msuN`),
// and when it is newer than the running build offers one button that hands
// the release zip to Decky Loader's own installer
// (`utilities/install_plugin`, install type UPDATE). Decky shows its usual
// confirmation, checks the zip against the SHA-256 GitHub reports for the
// asset, replaces the plugin and reloads it.
//
// The answer is cached for six hours so opening the panel does not spend the
// unauthenticated GitHub API budget. Any failure just hides the banner.

import { useEffect, useState, FC } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, Field } from "@decky/ui";

/** This build's version; must match plugin.json. */
export const FORK_VERSION = "0.33.1-msu8";
const PLUGIN_NAME = "Tender";
const RELEASES_API = "https://api.github.com/repos/taeminlee/romm-tender/releases?per_page=20";
const CACHE_KEY = "tender-fork-update";
const CACHE_MS = 6 * 60 * 60 * 1000;
const INSTALL_TYPE_UPDATE = 2; // decky-loader InstallType.UPDATE

interface ForkRelease {
  version: string;
  url: string;
  sha256: string;
}

type DeckyBackendLike = { call: (route: string, ...args: unknown[]) => Promise<unknown> };
type PluginLoaderLike = { plugins?: { name: string; version?: string }[] };
// decky-loader's frontend globals (window.DeckyBackend, window.DeckyPluginLoader)
const deckyGlobal = globalThis as unknown as { DeckyBackend?: DeckyBackendLike; DeckyPluginLoader?: PluginLoaderLike };

/** `0.33.1-msu5` → [0, 33, 1, 5]; anything else → null. */
export function forkVersionKey(v: string): number[] | null {
  const m = /^(\d+)\.(\d+)\.(\d+)(?:-msu(\d+))?$/.exec(v.trim());
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3]), Number(m[4] ?? 0)];
}

export function isNewer(candidate: string, current: string): boolean {
  const a = forkVersionKey(candidate);
  const b = forkVersionKey(current);
  if (!a || !b) return false;
  for (let i = 0; i < a.length; i++) {
    const x = a[i] ?? 0;
    const y = b[i] ?? 0;
    if (x !== y) return x > y;
  }
  return false;
}

/** The newer of this bundle's own version and the one Decky lists. Decky's list can lag behind a
 *  just-installed update until Steam restarts (msu7 fix), while the bundle constant is always current. */
function runningVersion(): string {
  try {
    const p = deckyGlobal.DeckyPluginLoader?.plugins?.find((x) => x.name === PLUGIN_NAME);
    if (p?.version && forkVersionKey(p.version) && isNewer(p.version, FORK_VERSION)) return p.version;
  } catch {
    /* fall back */
  }
  return FORK_VERSION;
}

interface GhAsset {
  name: string;
  browser_download_url: string;
  digest?: string | null;
}
interface GhRelease {
  tag_name: string;
  draft: boolean;
  prerelease: boolean;
  assets: GhAsset[];
}

async function fetchNewest(): Promise<ForkRelease | null> {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (raw) {
      const c = JSON.parse(raw) as { at: number; rel: ForkRelease | null };
      if (Date.now() - c.at < CACHE_MS) return c.rel;
    }
  } catch {
    /* no cache */
  }
  const r = await fetch(RELEASES_API, { headers: { Accept: "application/vnd.github+json" } });
  if (!r.ok) throw new Error(`GitHub ${r.status}`);
  const list = (await r.json()) as GhRelease[];
  let best: ForkRelease | null = null;
  for (const rel of list) {
    if (rel.draft || rel.prerelease) continue;
    const version = /^tender-v(.+)$/.exec(rel.tag_name)?.[1];
    if (!version || !forkVersionKey(version)) continue;
    const asset = rel.assets.find((a) => a.name === "Tender.zip");
    if (!asset) continue;
    const sha = asset.digest?.startsWith("sha256:") ? asset.digest.slice(7) : "";
    if (!best || isNewer(version, best.version)) best = { version, url: asset.browser_download_url, sha256: sha };
  }
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), rel: best }));
  } catch {
    /* ignore */
  }
  return best;
}

export const ForkUpdateBanner: FC = () => {
  const [rel, setRel] = useState<ForkRelease | null>(null);
  const [state, setState] = useState<"idle" | "asking" | "done" | "failed">("idle");
  const current = runningVersion();

  useEffect(() => {
    // Only inside Decky Loader (tests and other hosts have no installer to hand the zip to).
    if (!deckyGlobal.DeckyBackend) return;
    let alive = true;
    fetchNewest()
      .then((r) => {
        if (alive && r && isNewer(r.version, current)) setRel(r);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [current]);

  if (!rel) return null;

  const install = async () => {
    const backend = deckyGlobal.DeckyBackend;
    if (!backend) {
      setState("failed");
      return;
    }
    setState("asking");
    try {
      // Decky asks for confirmation, downloads, checks the hash and reloads the plugin.
      await backend.call(
        "utilities/install_plugin",
        rel.url,
        PLUGIN_NAME,
        rel.version,
        rel.sha256,
        INSTALL_TYPE_UPDATE,
      );
      // Decky has replaced the files; the panel may keep showing the old build until Steam restarts.
      setState("done");
    } catch {
      setState("failed");
    }
  };

  return (
    <PanelSection>
      <PanelSectionRow>
        <Field
          label={`새 버전 ${rel.version}`}
          description={
            state === "failed"
              ? "업데이트를 시작하지 못했습니다. Decky › 개발자 › URL 로 설치를 써 주세요."
              : state === "done"
              ? "설치를 요청했습니다. 확인 후 버전이 그대로 보이면 Steam 을 다시 시작하세요."
              : `지금 ${current}. 누르면 Decky 가 확인 후 설치하고 다시 불러옵니다.`
          }
          focusable={true}
          bottomSeparator="none"
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" bottomSeparator="none" disabled={state === "asking" || state === "done"} onClick={() => void install()}>
          {state === "asking" ? "Decky 확인 창을 확인하세요…" : state === "done" ? "설치 요청됨" : "업데이트"}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
};
