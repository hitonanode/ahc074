from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-perfint/main.cpp').read_text()
lo=s.index('template<int Capacity>\nstruct Perforation');hi=s.index('// ==== Design state:',lo)
b=s[lo:hi]
b=b.replace('    std::array<bool, P> cache_dirty{};','''    std::array<bool, P> cache_dirty{};
    std::array<uint32_t,P> dirty_samples{};
    int cache_sum=0;''',1)
b=b.replace('''                int i = u * kSamples + sample;
                cache[i] = make_cache(make_edges(u, samples[i],geometry));''','''                int i = u * kSamples + sample;
                if(!all && !(dirty_samples[u]>>sample&1U)) { ++cache_skips;continue; }
                cache_sum-=cache[i].value;
                cache[i] = make_cache(make_edges(u, samples[i],geometry));
                cache_sum+=cache[i].value;''',1)
b=b.replace('''        double sum = 0;
        for (const auto& q : cache) sum += q.value;
        return sum / (5 * kSamples);''','''        return double(cache_sum) / (5 * kSamples);''',1)
b=b.replace('''        cache_dirty.fill(true);  // the changed paper's own targets always need rebuilding''','''        cache_dirty.fill(true);  // the changed paper's own targets always need rebuilding
        dirty_samples.fill(~0U>>(32-kSamples));''',1)
old='''            same[u] = true;
            for (int b = 0; b < 2; b++)
                same[u] = same[u] && (signature(heads[c][b], opacity) == signature(heads[c][b], cache_opacity));
            cache_dirty[u] = !same[u];'''
new='''            same[u] = true;
            bool fixed_starts=true;
            for (int b = 0; b < 2; b++) {
                const auto before=signature(heads[c][b],cache_opacity);
                const auto after=signature(heads[c][b],opacity);
                same[u]=same[u]&&(before==after);
                fixed_starts=fixed_starts&&(before.second==after.second)&&!((before.first^after.first)&~changed);
            }
            cache_dirty[u] = !same[u];
            if(same[u])dirty_samples[u]=0;
            else if(fixed_starts) {
                // Only the changed handle's reward differs. Samples in which
                // that handle is already correct have exactly the same edges.
                uint32_t dirty=0;
                for(int sample=0;sample<kSamples;++sample)
                    if((samples[u*kSamples+sample]^target[u])&changed)dirty|=uint32_t(1)<<sample;
                dirty_samples[u]=dirty;
            }'''
assert old in b;b=b.replace(old,new,1)
b=b.replace('''        std::array<int16_t, P * kSamples> values;
        double sum = 0;''','''        int sum=cache_sum;''',1)
b=b.replace('''            if (s.ded[u] == k || same[u]) values[i] = q.value;
            else {''','''            if(s.ded[u]==k || !(dirty_samples[u]>>sample&1U))continue;
            {''',1)
b=b.replace('''                values[i] = value;

            }
            sum += values[i];''','''                sum+=value-q.value;
            }''',1)
b=b.replace('double upper = sum / (5 * kSamples) - profit;','double upper = double(sum) / (5 * kSamples) - profit;',1)
b=b.replace('''            values[i] = value;
          }
        }
        // Retain the original order of floating-point additions.
        sum = 0;
        for (double value : values) sum += value;''','''            sum+=value-q.value;
          }
        }
        // Every DP value is an exact small integer, so only changed rows need
        // to contribute a difference to the cached total.''',1)
b=b.replace('return sum / (5 * kSamples);','return double(sum) / (5 * kSamples);')
assert 'values[' not in b
s=s[:lo]+b+s[hi:]
d=ROOT/'solutions/deval-perfsparse';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-perfsparse

改良元: solutions/deval-perfint。

整数化した穴あけDPの総利益を差分で更新し、変わらない対象の行を走査・加算し直さない。穴の変更で辺の開始位置が同じなら、そのhandleが既に正しいサンプルでは辺も同じなのでDPキャッシュの再構築も省く。利益の式・採択基準・サンプルは親と同じ。探索予算と時間ガードは維持。
''')
print(len(s.encode()))
