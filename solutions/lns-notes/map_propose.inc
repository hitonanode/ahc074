        if (lns_map.active) {
            const u64 gm=lns_map.windows & ~hm, hh=lns_map.windows & hm;
            if(!gm)return false;
            const int a=select_bit(gm,rng.below(__builtin_popcountll(gm)));
            const int ea=which[a],kind=rng.below(10);
            int b=a,eb=ea,transfer=-1;bool swindow=false;
            if(kind<3 && hh) {
                b=select_bit(hh,rng.below(__builtin_popcountll(hh)));
                swindow=true;
            } else if(kind<6) {
                b=select_bit(gm,rng.below(__builtin_popcountll(gm)));
                eb=which[b];
                if(a==b || ea==eb)return false;
            } else if(kind<8) {
                if(counts[ea]<2)return false;
                eb=lns_map.groups[rng.below(lns_map.groups.size())];
                if(ea==eb)return false;
                transfer=eb;
            }
            mv={position[a],position[b],a,b,kind,ea,eb,transfer,swindow,mask[ea],mask[eb],pol};
            if(swindow) {
                mask[ea]^=(1ULL<<a)|(1ULL<<b);
                pol=(pol&~(1ULL<<b))|(u64(rng.next()&1)<<b);
                move_key=2*(64*a+b)+int(pol>>b&1);
            } else if(a!=b) {
                mask[ea]^=(1ULL<<a)|(1ULL<<b);mask[eb]^=(1ULL<<a)|(1ULL<<b);
                // Move the polarities together with the group assignments.
                if(((pol>>a)^(pol>>b))&1)pol^=(1ULL<<a)|(1ULL<<b);
                move_key=8256+64*a+b;
            } else if(transfer>=0) {
                mask[ea]&=~(1ULL<<a);mask[eb]|=1ULL<<a;
                pol=(pol&~(1ULL<<a))|(u64(rng.next()&1)<<a);
                move_key=12352+2*(ne*a+eb)+int(pol>>a&1);
            } else {
                pol^=1ULL<<a;move_key=8192+a;
            }
            memo_hit=memo_epoch[move_key]==2*epoch+1;
            if(memo_hit){++memo_hits;return true;}
            ++exact_evals;evaluate_pairs(ea,eb);return true;
        }
