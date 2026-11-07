from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
s=s.replace('    } post_context;','''    } post_context;
    // Only failed display filters are shared across passes of one request.
    // Full (paper,anchor) keys make collisions harmless. Tags cannot change display.
    struct NegativeTrial {
        std::array<uint16_t,32> key;
        unsigned generation=0;
        int size=0;
    };
    std::array<NegativeTrial,512> negative_trials;
    unsigned negative_generation=0;
    long long negative_hits=0,negative_checks=0;''',1)
s=s.replace('        post_context.ready = false;','        ++negative_generation;\n        post_context.ready = false;',1)
s=s.replace('''            EndMemo* memo = nullptr;
            bool memo_hit = false;''','''            NegativeTrial* negative=nullptr;
            if(trial.size()<=32) {
                std::array<uint16_t,32> key;
                u64 hash=0xcbf29ce484222325ULL^trial.size();
                for(int j=0;j<int(trial.size());++j) {
                    key[j]=uint16_t(trial[j].paper|(trial[j].anchor+1)<<8);
                    hash=(hash^key[j])*0x100000001b3ULL;
                }
                ++negative_checks;
                negative=&negative_trials[(hash^(hash>>32))&(negative_trials.size()-1)];
                if(negative->generation==negative_generation && negative->size==int(trial.size()) &&
                   std::memcmp(negative->key.data(),key.data(),trial.size()*sizeof(uint16_t))==0) {
                    ++negative_hits;return false;
                }
                negative->generation=negative_generation;
                negative->size=trial.size();
                std::memcpy(negative->key.data(),key.data(),trial.size()*sizeof(uint16_t));
            }
            EndMemo* memo = nullptr;
            bool memo_hit = false;''',1)
s=s.replace('''                if (view != A[u]) return false;
                if (cfg.memo) {''','''                if (view != A[u]) return false;
                if(negative)negative->generation=0; // success needs its own visibility replay
                if (cfg.memo) {''',1)
# Add buffered final diagnostics, outside request timing.
needle='    std::cerr << "f2_memo_hits = "'
idx=s.find(needle)
if idx>=0:s=s[:idx]+'''    std::cerr << "negative_checks = " << solver.negative_checks << "\\nnegative_hits = " << solver.negative_hits << '\\n';
'''+s[idx:]
d=ROOT/'solutions/deval-negative';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-negative

改良元: solutions/deval-vbranch-o3。

後処理で表示条件に落ちた編集列だけを注文内で記憶する。32編集以内の列は紙・差込み先を完全照合し、同じ失敗列の再計算を省く。表示に合う候補は毎回従来どおり可視性を確認する。浮動小数点演算、候補列挙、予算、時間ガードは変更しない。
''')
print(len(s.encode()),idx)
