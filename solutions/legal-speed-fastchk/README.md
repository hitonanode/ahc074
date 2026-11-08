# legal-speed-fastchk（legal-speed-fast の表示の見積りを確かめる版）

改良元: `solutions/legal-speed-fast`。SCREEN_CHECK を定義しただけで、出力は改良元と同じ。提出用ではない。

- 付け替えの試行の表示の見積り（screen）を使うたびに、その試行の並びを実際に作って表示を計算し、見積りと違った回数を `screen_mismatch`（調べた回数は `screen_checked`）に出す。0 なら、見積りで省いた試行はすべて、evaluate が最初の検査で落とすものだった。
