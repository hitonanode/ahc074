#!/usr/bin/env python3
"""計測とは別に固定回数で Annealer の差分状態を全再計算と照合する。"""
import argparse, concurrent.futures, hashlib, json, os, pathlib, re, subprocess
H=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--compiler',default='g++');p.add_argument('--g',type=int,default=36);p.add_argument('--seeds',default='24-32');a=p.parse_args()
source=H/(a.source+'.cpp');text=source.read_text()
text=text.replace('constexpr double kHelperGiveUp = 1.55;','constexpr double kHelperGiveUp = 1000.0;')
text=text.replace('int M = 6, G = 36;',f'int M = 6, G = {a.g};')
text=text.replace('''            double bestCost = cur;''','''            double bestCost = cur;
            double check_max=0;int check_count=0;''',1)
check='''                    if((it&65535)==0) {
                        // Check owner before rebuild, which itself reconstructs it.
                        for(int x=0;x<U;++x) {
                            const Unit& u=unit[x];
                            assert(D.owner[u.a]==x && (u.b<0 || D.owner[u.b]==x));
                            assert(!D.invalid_bit(u,u.c));
                            assert(key[x]==unit_key(u));
                        }
                        D.rebuild();
                        check_max=std::max(check_max,std::abs(D.cur-cur));++check_count;
                        if(std::abs(D.cur-cur)>0.1) {std::cerr << "MODEL MISMATCH " << D.cur << " " << cur << '\\n';std::abort();}
                        for(int c=0;c<H;++c) {
                            assert(cnc[c]==D.nc[c] && cnt[c]==D.nt[c] && cn1[c]==D.n1[c] && cp1[c]==D.pairOne[c]);
                            assert(cv[c]==colcost40(cnc[c],cnt[c],cn1[c],cp1[c]));
                            assert(n0[c]==D.hn[c][0] && n1[c]==D.hn[c][1]);
                            for(int j=0;j<H;++j) {
                                int t1=0,u1=0,p1=0,pd=0;
                                for(const Unit& u:unit) if(u.c==c) {
                                    const int b=D.hb[u.a]>>j&1;
                                    t1+=b;u1+=b;
                                    if(u.b>=0) {t1+=D.hb[u.b]>>j&1;p1+=b;pd+=(D.hb[u.a]^D.hb[u.b])>>j&1;}
                                }
                                assert(rows[c].t1[j]==t1 && rows[c].u1[j]==u1 && rows[c].p1[j]==p1 && rows[c].pd[j]==pd);
                            }
                        }
                    }
'''
needle='''                if ((it & 255) == 0) {
                    double elapsed ='''
assert text.count(needle)==1
text=text.replace(needle,'''                if ((it & 255) == 0) {
'''+check+'''                    double elapsed =''',1)
text=text.replace('''            unit = best;
            D.handle = bestHandle;''','''            std::cerr << "check_states = " << check_count << "\\ncheck_drift = " << check_max << '\\n';
            unit = best;
            D.handle = bestHandle;''',1)
name=f'check-{a.source}-g{a.g}'+('-clang' if a.compiler=='clang++' else '')
src=H/(name+'.cpp');src.write_text(text)
cmd=[a.compiler,'-std=c++23','-O2','-DCLOCK_SCALE=1.1','-DSIM_HARNESS',str(src),'-o',str(H/name)]
subprocess.run(cmd,check=True)
env=os.environ.copy();env.update(SIM_SEQS='1',MAP_ITERS='1110000',GOPT_STEPS='353500',ANNEAL_ITERS='5000000',CLIMB_ITERS='-1')
def run(seed):
 with (H.parents[1]/'tools/in'/f'{seed:04}.txt').open('rb') as f:
  r=subprocess.run([str(H/name)],stdin=f,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=env,timeout=60)
 txt=r.stderr.decode();vals={k:float(v) for k,v in re.findall(r'^([A-Za-z_][A-Za-z_0-9]*) = ([-+0-9.eE]+)$',txt,re.M)}
 if r.returncode or vals.get('sim_wrong')!=0 or vals.get('check_states',0)==0:
  (H/(name+f'-error-{seed}.txt')).write_text(txt);raise RuntimeError((seed,r.returncode,txt))
 return dict(seed=seed,**vals)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(run,range(*map(int,a.seeds.split('-')))))
result=dict(config=vars(a),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),command=cmd,rows=rows)
(H/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(name, 'cases',len(rows),'states',sum(r['check_states'] for r in rows),'max_drift',max(r['check_drift'] for r in rows))
