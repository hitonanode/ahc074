"""実行可能な近傍が尽きた状態のみ、損失の上限を1対緩める。"""
def rescue(t,interval):
    t=t.replace('constexpr int kRejectLoss = 3, kMemoSize = 1 << 18;', 'int kRejectLoss = 3;\n    constexpr int kMemoSize = 1 << 18;')
    t=t.replace('(eight | four | (twos & ones))','(eight | four | (kRejectLoss==3 ? (twos & ones) : 0U))')
    old='''                rejected[b] |= twice[b]&bad; twice[b] |= ones[b]&bad; ones[b] ^= bad;'''
    new='''                const uint32_t carry=ones[b]&bad, carry2=twice[b]&carry;
                ones[b]^=bad; twice[b]^=carry; rejected[b]|=carry2;'''
    assert old in t;t=t.replace(old,new,1)
    t=t.replace('options[b] = allowed & ~rejected[b];', 'options[b] = allowed & ~(rejected[b] | (kRejectLoss==3 ? (ones[b]&twice[b]) : 0U));',1)
    t=t.replace('    auto apply_move = [&](const Move& mv) {', '    auto apply_move = [&](const Move& mv) {\n        kRejectLoss=3;',1)
    needle='    long long forced_steps = 0, tabu_skips = 0;'
    t=t.replace(needle,'    long long loss_relaxations=0;\n'+needle,1)
    code='''        if ((it&255)==0 && !escape_valid && it-last_accept_it>=INTERVAL && kRejectLoss==3) {
            // Every available neighbor can be screened out. Rebuild candidate tables with
            // a one-pair wider screen; normal acceptance restores the original threshold.
            kRejectLoss=4; ++epoch; ++loss_relaxations;
        }
'''.replace('INTERVAL',str(interval))
    t=t.replace('        if (it - last_accept_it >= kMapStall',code+'        if (it - last_accept_it >= kMapStall',1)
    t=t.replace('            if (it - last_accept_it >= kClimbStall',code+'            if (it - last_accept_it >= kClimbStall',1)
    t=t.replace('    stats.gobj_before = cur;', '    kRejectLoss=3;\n    stats.gobj_before = cur;',1)
    t=t.replace('    stats.gobj_after = cur;',r'''    std::cerr << "loss_relaxations = " << loss_relaxations << '\n';
    stats.gobj_after = cur;''',1)
    return t
