改良元: solutions/lns-star（注文処理は solutions/deval-helper-wide と同一）

研究用の固定予算。LNS_MODE 1=領域の破壊修復、2=追加 anneal branches、3=追加 refinishes、4=全設計の独立再実行、5=完成済み最良設計の再焼きなまし、6=比較紙の集合をまたぐ比較窓の極性を一括反転。詳細は lns-star/README.md。

既定設定:

```json
{
  "name": "lns-deepmap2",
  "mode": 1,
  "steps": 2,
  "map": 150000,
  "anneal": 2000000,
  "finishes": 2,
  "groups": 5,
  "handles": 4,
  "temperature": 0.15,
  "kick": -1,
  "first": 0,
  "release_mode": 1,
  "keep_columns": 1,
  "transfer": 0,
  "cut": 0,
  "cutoff": 26,
  "exact": 0,
  "missing": 10.0,
  "map_match": 0,
  "base_map": 450000,
  "base_anneal": 11175000,
  "preferred": 0,
  "preferred_weight": 0.15,
  "soft": 0.0,
  "min_windows": 2
}
```

時間超過を許す研究版のため、評価は --no-record を付ける。全ケースは標準 pahcer_run.py から実行する。

窓修復を15万反復まで延ばし、親と最低2窓異なる訪問状態を返す。短い修復で目的値が高止まりする問題を切り分ける。各修復は2M列焼きなましと3仕上げまで完了する。既定2回、LNS_MULTIPLIER=7なら14回。固定回数2/6/14回時点の最良設計を保存すれば、後続探索や注文情報を使わず各予算を再生できる。
