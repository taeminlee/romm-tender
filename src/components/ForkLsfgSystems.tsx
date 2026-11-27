// Fork addition (0.33.1-msu8): frame generation (decky-lsfg-vk) on or off per RetroDECK system,
// shown under Settings › Advanced. Writes ~/.config/romm-tender/lsfg-systems (py_modules/fork_lsfg.py),
// which bin/rom-launcher reads at every game start.

import { useEffect, useState, FC } from "react";
import { PanelSection, PanelSectionRow, Field, ToggleField } from "@decky/ui";
import { getForkLsfg, setForkLsfg, ForkLsfgStatus } from "../api/backend";

export const ForkLsfgSystems: FC = () => {
  const [st, setSt] = useState<ForkLsfgStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getForkLsfg()
      .then((r) => alive && setSt(r))
      .catch((e) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, []);

  const toggle = async (name: string, enabled: boolean) => {
    setBusy(name);
    try {
      const r = await setForkLsfg(name, enabled);
      if (!r.success) {
        setError(r.message);
        return;
      }
      setSt((cur) =>
        cur && { ...cur, systems: cur.systems.map((s) => (s.name === name ? { ...s, enabled: r.enabled } : s)) },
      );
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  let description = "다음 실행부터 적용됩니다. 화면 주사율과 어긋나는 기종(PC-98 등)은 끄는 편이 매끄럽습니다.";
  if (error) description = `설정하지 못했습니다: ${error}`;
  else if (!st) description = "불러오는 중…";
  else if (!st.available) description = "decky-lsfg-vk 의 ~/lsfg 스크립트가 없어 지금은 어떤 게임에도 쓰이지 않습니다.";
  else if (st.systems.length === 0) description = "RetroDECK 롬 폴더에 설치된 게임이 없습니다.";

  return (
    <PanelSection title="프레임 생성">
      <PanelSectionRow>
        <Field label="기종별 lsfg" description={description} focusable={true} bottomSeparator="none" />
      </PanelSectionRow>
      {st?.systems.map((s) => (
        <PanelSectionRow key={s.name}>
          <ToggleField
            label={s.name}
            checked={s.enabled}
            disabled={busy !== null}
            onChange={(v: boolean) => void toggle(s.name, v)}
            bottomSeparator="none"
          />
        </PanelSectionRow>
      ))}
    </PanelSection>
  );
};
