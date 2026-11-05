"""Isolated feature ablations; every source starts from time-alloc."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
base=(ROOT/'solutions/time-alloc/main.cpp').read_text()

def emit(name,src,description):
    folder=ROOT/'solutions'/('clean-design-'+name)
    folder.mkdir(exist_ok=True)
    (folder/'main.cpp').write_text(src)
    (folder/'README.md').write_text('改良元: solutions/time-alloc\n\n'+description+'\n\n'
        'この機能だけを無効にした寄与の測定用コピー。他の反復数・乱数生成器・設定は変更しない。\n'
        '共有の環境変数を使わず、ソースで無効にする。ログとプロファイラは残す。\n')

start=base.index('    Perforation perforation(solver);')
end=base.index('    return state;',start)
src=base[:start]+'''    std::cerr << "perforation_holes = 0\\nperforation_trials = 0\\nperforation_accepts = 0"
              << "\\nperforation_sec = " << elapsed_sec() - perforation_start
              << "\\nperforation_end_sec = " << elapsed_sec() << '\\n';
'''+base[end:]
emit('noperf',src,'最終のハンドル穿孔を行わない。専用紙の模様は再割当直後のまま。perforation_* の件数は0。')

start=base.index('        {\n            auto g = head.probability_gradient();')
end=base.index('        // tail[a][j]',start)
emit('nograd',base[:start]+base[end:],
     'Hungarian 費用の、列先頭の色確率が変わることによるフィラー利益の勾配だけを除く。直接の穴費用とフィラー利益は残す。')

needle='                    column_swap(a, a + d);'
assert base.count(needle)==1
emit('nocolswap',base.replace(needle,'                    (void)a;  // Ablation: no whole-column swap.'),
     '列とそのハンドルをまとめて交換する焼きなまし近傍を無効にする。候補選択の乱数は消費する。colswap_* は0。')

start=base.index('                int best_priority = 1 << 30;')
end=base.index('                const int code = select_bit(available,',start)
src=base[:start]+base[end:]
# The ranking is not used anywhere else, so omit its expensive calculation too.
start=src.index('        // Compute only the destinations surviving the loss screen.')
end=src.index('        return available;',start)
src=src[:start]+src[end:]
emit('norank',src,'窓を別のシート対へ移すとき、汎用層費用による移動先の順位付けをやめる。整合性の足切りを通る未試行候補から一様に選ぶ。')

pos=base.index('        if (cross_move) {  // generic window a -> handle')
emit('nogeneric',base[:pos]+'        if (!swindow && kind < 8) return false;  // No ordinary flips/exchanges.\n'+base[pos:],
     '窓割当の通常近傍から、汎用窓の単独反転と汎用窓同士のシート対交換を除く。保存状態への経路探索の反転・移動は残す。')
emit('notabu',base.replace('kTabuAccepted = 4','kTabuAccepted = 0'),
     '窓割当で、受理した変更を逆向きへ戻す短期タブーを無効にする。停滞からの脱出と保存状態への経路探索は残す。tabu_skips は0。')
