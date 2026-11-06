改良元: solutions/nogen-budget

同色キャップのペア制約を含む64窓の所有監査を引き継ぎ、時間配分を変更する。
背景窓の割り当ては12,000反復。背景層に補助紙を2枚置く候補は安価な6組を調べ、
実際の操作生成と後処理は最良2案だけに行う。補助紙1枚も最良2案まで。
背景紙を主紙とする別経路は既定で無効（V5_ALTERNATE=0）。通常の所有商品紙は全商品に残る。

その他の設計・注文処理と指標は改良元のまま。`NG_CONTROL_MAP` は12,000、
`V4_JOINT_LIMIT` は6が既定。1枚・2枚案の採用上限2はコード内定数。
`audit_owner_violations`、`audit_unowned_papers` は64窓での違反数で、LOCAL_BENCHでは違反時に停止する。
`ng_base_sec` / `ng_helper_sec` / `ng_alternate_sec` は通常計画・補助紙探索・別主紙探索の時間。
`helper_end_sec` / `req_sec` / `end_sec`、DesignStore、紙属性・操作ラベルを維持する。
