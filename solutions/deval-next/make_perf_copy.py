from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/deval-seven-wide/main.cpp').read_text()
s=s.replace('''        for (auto [k, c] : candidates) {
            trials++;''','''        std::array<double,K> old_utility;
        std::array<double,P> old_row;
        for (auto [k, c] : candidates) {
            trials++;''',1)
s=s.replace('''            auto old_utility = utility, old_row = gains[k];''','''            std::copy(utility.begin(),utility.end(),old_utility.begin());
            std::copy(gains[k].begin(),gains[k].end(),old_row.begin());''',1)
s=s.replace('''                utility = std::move(old_utility);
                gains[k] = std::move(old_row);''','''                std::copy(old_utility.begin(),old_utility.end(),utility.begin());
                std::copy(old_row.begin(),old_row.end(),gains[k].begin());''',1)
p=r/'solutions/deval-perf-copy';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n穴あけでの変更取消し用配列をスタック上に確保し、毎回のvector確保と解放を省く。浮動小数点の演算順、候補順、固定予算は同じ。時間による打切りはない。\n')
