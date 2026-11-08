改良元: solutions/lns-star（注文処理は solutions/deval-helper-wide と同一）

研究用の固定予算。LNS_MODE 1=領域の破壊修復、2=追加 anneal branches、3=追加 refinishes、4=全設計の独立再実行、5=完成済み最良設計の再焼きなまし、6=比較紙の集合をまたぐ比較窓の極性を一括反転。詳細は lns-star/README.md。

既定設定:

```json
{
  "name": "lns-soft",
  "mode": 1,
  "steps": 4,
  "map": 25000,
  "anneal": 2000000,
  "finishes": 2,
  "groups": 5,
  "handles": 4,
  "temperature": 0.3,
  "kick": -1,
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

窓の修復途中は不適合な共有ペアも有限の矛盾罰則（LNS_SOFT_PENALTY=1.0）で扱う。両向きの比較制約数（長いcycleなら最低1）を近似罰則にする。71ペアすべて適合する訪問状態を優先して返す。その後の列修復では必ず真の互換グラフを使い、完成候補の合法性は緩めない。
