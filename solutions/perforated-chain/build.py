from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-eight/main.cpp').read_text()
old='''        for(auto&bits:samples)for(int c=0;c<H;c++)if((random()>>11)*0x1.0p-53<probability[c][1])bits|=1ULL<<c;'''
assert old in s
new='''        // A request changes several column heads together. Sample that
        // joint process instead of independently sampling each marginal.
        // Return events use the same 2 * demand rate as the design model.
        u64 sampled_colors=0,majority=0;
        for(int c=0;c<H;c++)if(counts[c][1]>counts[c][0])majority|=1ULL<<c;
        int stored=0;
        for(int t=0;stored<int(samples.size());t++){
            int u=random()%P;
            u64 holes=low_bits(H)&~opacity[s.ded[u]];
            sampled_colors=(sampled_colors&~holes)|(target[u]&holes);
            for(int r=0;r<2;r++){
                int c=columns[s.ded[random()%P]];u64 bit=1ULL<<c;
                sampled_colors=(sampled_colors&~bit)|(majority&bit);
            }
            if(t>=4096&&(t&7)==0)samples[stored++]=sampled_colors;
        }'''
s=s.replace(old,new)
(p/'main.cpp').write_text(s)
