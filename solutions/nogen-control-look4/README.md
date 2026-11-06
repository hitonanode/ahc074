改良元: solutions/nogen-helper-order

背景6商品紙の並べ替え先を、今回の距離と将来の背景操作の期待費用で選ぶ。
既存のControlTable::build_valuesを有効にし、Bellman更新は4回、PC_LOOKの既定値を1.0とする。
全256商品が等確率という問題の生成分布を使い、未来の実注文は読まない。
背景以外の列評価、候補数、印刷設計は変えない。所有者監査・時間ガード・DesignStore v2を維持。
