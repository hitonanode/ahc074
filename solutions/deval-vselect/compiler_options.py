def design_o3(src):
    """The two exact regions tested in deval-vo3; no fast-math changes."""
    assert '#pragma GCC optimize("O3")' not in src
    for begin,end in [('Generic layer: the comparator of the six sheets','Solver: papers, handles and the generic look-ahead'),
                      ('Handle perforation','Saving and loading the design state (LOCAL_BENCH: DesignStore)')]:
        start='// ==== '+begin+' ===='
        assert start in src
        src=src.replace(start,'#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC push_options\n#pragma GCC optimize("O3")\n#endif\n'+start)
        finish='// ==== '+end+' ===='
        if end.startswith('Saving'):finish='#ifdef LOCAL_BENCH\n'+finish
        assert finish in src
        src=src.replace(finish,'#if defined(__GNUC__) && !defined(__clang__)\n#pragma GCC pop_options\n#endif\n'+finish)
    return src
