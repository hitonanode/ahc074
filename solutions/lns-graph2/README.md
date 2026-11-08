改良元: solutions/lns-star（注文処理は solutions/deval-helper-wide と同一）

研究用の固定予算。LNS_MODE 1=領域の破壊修復、2=追加 anneal branches、3=追加 refinishes、4=全設計の独立再実行、5=完成済み最良設計の再焼きなまし。詳細は lns-star/README.md。

既定設定:

```json
{
  "name": "lns-graph2",
  "mode": 1,
  "steps": 3,
  "map": 25000,
  "anneal": 2000000,
  "finishes": 2,
  "groups": 5,
  "handles": 4,
  "temperature": 0.6,
  "kick": -1,
  "first": 0,
  "release_mode": 1,
  "keep_columns": 1,
  "cutoff": 28,
  "exact": 1,
  "missing": 2.0,
  "map_match": 1,
  "base_map": 450000,
  "base_anneal": 11175000
}
```

時間超過を許す研究版のため、評価は --no-record を付ける。全ケースは標準 pahcer_run.py から実行する。
