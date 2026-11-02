"""少数の全対評価を集めてから最小費用候補を受理判定する。"""
def batch(t,n):
    t=t.replace('    auto apply_move = [&](const Move& mv) {','    int state_evals=0;\n    auto apply_move = [&](const Move& mv) {\n        state_evals=0;',1)
    t=t.replace('const double candidate = memo_hit ?', 'double candidate = memo_hit ?')
    for stall in ['kMapStall','kClimbStall']:
        needle=f'        const bool force = it - last_accept_it >= {stall}'
        pos=t.index(needle)
        code='''        ++state_evals;
        if (state_evals<N && it-last_accept_it<STALL) { undo_move(mv); continue; }
        // Pick the best exact neighbor seen in this state once the small initial batch is ready.
        if (escape_floor<candidate) {
            undo_move(mv); install_escape(); candidate=escape_floor;
        }
'''.replace('state_evals<N',f'state_evals<{n}').replace('STALL',stall)
        t=t[:pos]+code+t[pos:]
    return t
