改良元: solutions/lns-star（注文処理は solutions/deval-helper-wide と同一）

研究用の固定予算。LNS_MODE 1=領域の破壊修復、2=追加 anneal branches、3=追加 refinishes、4=全設計の独立再実行、5=完成済み最良設計の再焼きなまし、6=比較紙の集合をまたぐ比較窓の極性を一括反転。詳細は lns-star/README.md。

既定設定:

```json
{
  "name": "lns-cut-warmhole",
  "mode": 6,
  "steps": 7,
  "map": 20000,
  "anneal": 2000000,
  "finishes": 2,
  "groups": 5,
  "handles": 4,
  "temperature": 0.12,
  "kick": -1,
  "first": 0,
  "release_mode": 2,
  "keep_columns": 1,
  "transfer": 1,
  "cut": 1,
  "cutoff": 26,
  "exact": 0,
  "missing": 10.0,
  "map_match": 0,
  "base_map": 450000,
  "base_anneal": 11175000
}
```

時間超過を許す研究版のため、評価は --no-record を付ける。全ケースは標準 pahcer_run.py から実行する。
