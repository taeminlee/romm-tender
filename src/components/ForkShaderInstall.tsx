// Fork addition (0.33.1-msu6): install the RomM server's RetroArch shader bundle from the QAM
// (py_modules/fork_shaders.py), shown under Settings › Advanced. Replaces the `curl … install-shaders.sh | bash` terminal step.

import { useState, FC } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, Field } from "@decky/ui";
import { installForkShaders } from "../api/backend";

type State = { kind: "idle" } | { kind: "working" } | { kind: "done"; text: string } | { kind: "failed"; text: string };

const IDLE_TEXT = "서버의 CuNNy · MMPX+CuNNy · CRT · LCD 셰이더를 RetroArch 에 설치하거나 새 버전으로 바꿉니다.";

export const ForkShaderInstall: FC = () => {
  const [state, setState] = useState<State>({ kind: "idle" });

  const run = async () => {
    setState({ kind: "working" });
    try {
      const r = await installForkShaders();
      if (r.success) {
        setState({
          kind: "done",
          text: `설치됨: 조합 프리셋 ${r.presets.length}개. RetroArch › 셰이더 › 프리셋 불러오기 › shaders_slang › hb-upscale`,
        });
      } else {
        setState({ kind: "failed", text: r.message });
      }
    } catch (e) {
      setState({ kind: "failed", text: `설치하지 못했습니다: ${String(e)}` });
    }
  };

  const description =
    state.kind === "done" || state.kind === "failed" ? state.text : state.kind === "working" ? "받는 중…" : IDLE_TEXT;

  return (
    <PanelSection title="셰이더">
      <PanelSectionRow>
        <Field label="RetroArch 셰이더" description={description} focusable={true} bottomSeparator="none" />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          bottomSeparator="none"
          disabled={state.kind === "working"}
          onClick={() => void run()}
        >
          {state.kind === "working" ? "설치 중…" : "셰이더 설치 / 업데이트"}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
};
