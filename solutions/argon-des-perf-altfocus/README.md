改良元: solutions/argon-des-perf-latew105

穿孔後再割当の後、現在のhead・模様・色確率で穿孔をもう一巡する。
新しい穴の追加と既存穴の復元を許し、自然なペア穴と自身のハンドルは守る。
新しい穴の対象は所有目標が移動した紙と新しく選ばれたhead。
既存穴の復元はhead以外の紙にも許す。穿孔係数0.7、32層化標本・owner条件付き評価を維持。
再穿孔の後には再割当を行わない対照。

ARGON_D2_ALT_PASSESは追加段の反復数（既定1、0で追加段なし）。
d2_alt_*は試行・受理・追加穴・復元穴・費用と価値の差・時間。
d2_altmatch_*、d2_altmodel_*、d2_altfiller_*は最後の再割当の量と費用・価値。
元のログ・全スイッチ・プロファイラ・DesignStore・段の目印を保持。
新しい段はdesign_papers: alternating perforation and reassignment。
