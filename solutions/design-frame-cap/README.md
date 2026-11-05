改良元: solutions/esw-clean

窓の割当の直後・列配置の前に、汎用窓以外の26窓から cap を選ぶ。
比較器とその可解な対は固定し、cap を除いたハンドル差を使う71対の貪欲費用が最小の窓を選ぶ。
その後は通常どおり全ての列・ハンドル順・共有対を最適化する。
既存の列を修復する cap 交換とは異なり、この時点では列がないので修復は不要。

選んだ物理窓を内部の窓63へ移し、DesignStore の permutation と A も整合させる。
FRAME_CAP=0 で無効。通常のログ・設定・プロファイラ・紙属性・操作ラベルは維持する。
追加指標は frame_cap_changed、frame_cap_before / after / gain（割当の目的値）、frame_cap_sec。
既存の cap_window は最終的な物理窓番号を表す。gobj_after は cap 選択前の従来の値。
