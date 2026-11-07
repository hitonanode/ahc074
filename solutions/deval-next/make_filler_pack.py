from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/deval-seven-wide/main.cpp').read_text()
a='''    struct Filler {
        int paper;
        int lvl = 0, hi = 0;
    };'''
b='''    struct Filler {
        // Paper IDs fit int16 (including -1); handle levels are 0..63.
        int16_t paper;
        int8_t lvl, hi;
        Filler(int p=-1,int l=0,int h=0):paper(int16_t(p)),lvl(int8_t(l)),hi(int8_t(h)){}
    };'''
assert a in s;s=s.replace(a,b,1)
p=r/'solutions/deval-filler-pack';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\nfillerの状態記録を12から4バイトに詰める。紙番号は符号付き16ビット、ハンドルの上下端は符号付き8ビットで全ての値を保つ。探索状態のコピーと作業配列を小さくする。候補、計算、固定予算は同じで、時間による打切りはない。\n')
