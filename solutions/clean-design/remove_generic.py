"""Remove ordinary generic flips/exchanges, preserving the ablation's RNG stream."""
from pathlib import Path
import sys

def remove_generic(s):
    s=s.replace('    const int as_screen = std::getenv("AS_SCREEN") ? env_int("AS_SCREEN") : 1;',
                '    constexpr int as_screen = 0;  // Its ordinary-move screen is no longer used.')
    s=s.replace('    std::array<Colors, 64> direct_remaining{};\n','')
    s=s.replace('    std::array<unsigned char, 64> direct_ready{};\n','')
    s=s.replace('            direct_ready = {};\n','')
    start=s.index('    // Opposite arcs on either changed sheet pair prove incompatibility')
    end=s.index('    // Cache exact objective values',start)
    s=s[:start]+s[end:]
    pos=s.index('        if (cross_move) {  // generic window a -> handle')
    s=s[:pos]+'''        // Retain the same proposal draws and budget for the remaining moves.
        // These slots used to propose ordinary generic flips/exchanges.
        if (!swindow && kind < 8) return false;
'''+s[pos:]
    start=s.index('        } else if (kind < 3) {  // flip the colors of a')
    end=s.index('        } else {  // window a to another pair',start)
    s=s[:start]+s[end:]
    start=s.index('        else if (kind < 3)\n            move_key = 8192 + a;')
    end=s.index('        else\n            move_key = 12352',start)
    s=s[:start]+s[end:]
    start=s.index('        // Window replacements and transfers have already passed their candidate tables.')
    end=s.index('        exact_evals++;',start)
    s=s[:start]+s[end:]
    s=s.replace('            if (mv.kind >= 3 && mv.kind < 8) std::swap(which[mv.a], which[mv.b]);\n','')
    # No remaining operation stores a rejected-neighbor tag. Keep diagnostic names.
    start=s.index('        if (memo_epoch[move_key] == 2 * epoch) {')
    end=s.index('        memo_hit = memo_epoch[move_key] == 2 * epoch + 1;',start)
    s=s[:start]+s[end:]
    s=s.replace('memo_epoch[key] == 2 * epoch || memo_epoch[key] == 2 * epoch + 1',
                'memo_epoch[key] == 2 * epoch + 1')
    s=s.replace('        // Keys distinguish the new polarity; exchanges of two generic windows are unordered.',
                '        // Keys distinguish the destination sheet pair and polarity.')
    return s

if __name__=='__main__':
    Path(sys.argv[2]).write_text(remove_generic(Path(sys.argv[1]).read_text()))
