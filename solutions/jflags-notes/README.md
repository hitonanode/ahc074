# jflags-notes（ジャッジのビルドの flags の影響を測る道具とメモ）

改良元: なし（解法ではない）。

- `run.py`: 標準の runner（scripts/pahcer_run.py）に、腕ごとのコンパイラと flags を足しただけのもの（dcomp-notes/task10_run.py を手本にした）。環境変数 `JFLAGS_ARMS` に、腕の順に `[コンパイラ, "flags"]` の JSON の列を渡す（flags は標準の "-std=c++23 -O2" を置き換え、-DCLOCK_SCALE=1.1 -DLOCAL_BENCH は常に足す）。同じ解法を何度でも並べられる（run-id に -2, -3 … が付く）。ビルドは評価のロックの下で nice（`JFLAGS_HELD=1` なら、呼ぶ側がロックを持っているとして nice だけ）。腕の flags は meta.json の `jflags` に残る。評価・時間・ロック・記録・解法の扱いは標準のまま。
- `flag_table.py`: 1 回の比較の腕ごとの段の時間（map_end・climb_end・anneal_end・helper_end・req・end、ジャッジの模型）と、腕の組の同じ seed どうしの差、stdout が違う seed の数。
- 調べた経過と結果は PROGRESS.md。
