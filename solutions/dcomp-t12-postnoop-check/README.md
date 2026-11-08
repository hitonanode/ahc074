改良元: solutions/dcomp-t12-postmemo

postが一度もbestを更新しなかった場合、終状態・操作・ラベルは呼出し入力そのものなので、結果のcopyを保存せずunchanged bitで記録する。hitでも入力をそのまま返す。入力key全体の一致とeject_accepts差の再現は保持。検証版はno-opでも元処理と全出力を照合する。

探索・選択は変えず、時計で切り替えない。ログ・trace・profiler・実験switch・段・DesignStoreを保持する。
