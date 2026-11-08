改良元: solutions/lns-star（注文処理は solutions/deval-helper-wide と同一）

研究用の固定予算。LNS_MODE 1=領域の破壊修復、2=追加 anneal branches、3=追加 refinishes、4=全設計の独立再実行、5=完成済み最良設計の再焼きなまし、6=比較紙の集合をまたぐ比較窓の極性を一括反転。詳細は lns-star/README.md。

既定設定:

```json
{
  "name": "lns-preferred",
  "mode": 1,
  "steps": 5,
  "map": 25000,
  "anneal": 2000000,
  "finishes": 2,
  "groups": 5,
  "handles": 4,
  "temperature": 0.3,
  "kick": 0,
  "first": 0,
  "release_mode": 1,
  "keep_columns": 1,
  "transfer": 0,
  "cut": 0,
  "cutoff": 26,
  "exact": 0,
  "missing": 2.0,
  "map_match": 0,
  "base_map": 450000,
  "base_anneal": 11175000
}
```

時間超過を許す研究版のため、評価は --no-record を付ける。全ケースは標準 pahcer_run.py から実行する。

修復前に領域外で矛盾しない新しい近接8ペアを選び、その互換性を窓修復の目的に加える（LNS_PREFERRED_WEIGHT=0.15）。旧ペアの喪失は足切りせず、列修復では互換化できた希望ペアを先に配置する。完成後のVでのみ最終候補を選ぶ。
