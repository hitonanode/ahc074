from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1];p=root/'solutions/deval-helper-hash2';p.mkdir()
s=(root/'solutions/deval-helper-wide/main.cpp').read_text()
a='''                    u64 hash = 0xcbf29ce484222325ULL;
                    for (int j = 0; j + 8 <= K; j += 8) {
                        u64 word;
                        std::memcpy(&word, next.data() + j, 8);
                        hash = (hash ^ word) * 0x100000001b3ULL;
                    }
'''
b='''                    u64 hash = 0xcbf29ce484222325ULL, h1=0x9e3779b97f4a7c15ULL;
                    for (int j=0;j+16<=K;j+=16) {
                        u64 a,b;std::memcpy(&a,next.data()+j,8);std::memcpy(&b,next.data()+j+8,8);
                        hash=(hash^a)*0x100000001b3ULL;h1=(h1^b)*0x100000001b3ULL;
                    }
                    hash^=(h1<<32)|(h1>>32);
'''
assert s.count(a)==1;s=s.replace(a,b);assert len(s.encode())<=522000
(p/'main.cpp').write_text(s);(p/'README.md').write_text('''改良元: `solutions/deval-helper-wide`。

後処理のfinal-state memoのhashを2本の独立な整数積へ分け、最後に混ぜる。従来と同じ全successor配列の一致検査を保持するため、hash衝突は誤ったcache hitにはならない。memoの置換位置だけが変わる。固定予算・探索順・浮動小数点計算・設計・操作ラベルとログは保つ。時刻による切替えはない。hashの変更が操作列と速度へどう影響するかを測る出力同一実験。
''');print(len(s.encode()))
