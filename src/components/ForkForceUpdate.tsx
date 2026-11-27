// Fork addition (0.33.1-msu9): reinstall the newest fork release from Settings › Advanced, so nobody has to
// type the release URL into Decky › Developer. Asks GitHub fresh (no cache) and hands the zip to Decky's own
// installer, which confirms, checks the SHA-256 GitHub reports and reloads the plugin.

import { useState, FC } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, Field } from "@decky/ui";
import {
  fetchNewest,
  installRelease,
  isNewer,
  runningVersion,
  INSTALL_TYPE_REINSTALL,
  INSTALL_TYPE_UPDATE,
} from "./ForkUpdateBanner";

type State = "idle" | "checking" | "asking" | "done" | "failed";

export const ForkForceUpdate: FC = () => {
  const [state, setState] = useState<State>("idle");
  const [text, setText] = useState<string | null>(null);
  const current = runningVersion();

  const run = async () => {
    setState("checking");
    setText(null);
    try {
      const rel = await fetchNewest(true);
      if (!rel) {
        setState("failed");
        setText("GitHub 에서 설치할 릴리스를 찾지 못했습니다.");
        return;
      }
      setState("asking");
      const type = isNewer(rel.version, current) ? INSTALL_TYPE_UPDATE : INSTALL_TYPE_REINSTALL;
      if (!(await installRelease(rel, type))) {
        setState("failed");
        setText("Decky 설치 기능에 연결하지 못했습니다.");
        return;
      }
      setState("done");
      setText(`${rel.version} 설치를 요청했습니다. Decky 확인 후, 버전이 그대로 보이면 Steam 을 다시 시작하세요.`);
    } catch (e) {
      setState("failed");
      setText(`업데이트하지 못했습니다: ${String(e)}`);
    }
  };

  const busy = state === "checking" || state === "asking";
  const description =
    text ??
    (state === "checking"
      ? "GitHub 에서 최신 버전을 확인하는 중…"
      : state === "asking"
        ? "Decky 확인 창을 확인하세요…"
        : `지금 ${current}. 최신 릴리스를 바로 받아 설치합니다(같은 버전이면 다시 설치).`);

  return (
    <PanelSection title="Tender 업데이트">
      <PanelSectionRow>
        <Field label="최신 버전 설치" description={description} focusable={true} bottomSeparator="none" />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" bottomSeparator="none" disabled={busy} onClick={() => void run()}>
          {busy ? "진행 중…" : "최신 버전 다시 설치"}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
};
