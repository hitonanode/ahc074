// functions.exec 用。load("astra_design_measure") に {label,binaries,sim,seeds:[start,end]} を設定する。
// 管理用の常駐OSプロセスを置かず、12本の解法をツールから直接実行する。
const cfg=load('astra_design_measure');
const root='/home/sato/ahc074/.claude/worktrees/clean-base-optimization-1b199f';
const dir=root+'/solutions/astra-design';
const start=cfg.seeds?.[0]??24,end=cfg.seeds?.[1]??88;
const rows=[];
const measured=end-start,total=cfg.pad?Math.ceil(measured/12)*12:measured;
const clean='env -u MAP_ITERS -u GOPT_STEPS -u ANNEAL_ITERS -u CLIMB_ITERS -u SIM_SEQS ';
const fixed=cfg.sim?'SIM_SEQS=8 MAP_ITERS=1110000 GOPT_STEPS=353500 CLIMB_ITERS=66500 ':'';
const tasks=Array.from({length:12},(_,slot)=>(async()=>{
 for(let pos=slot;pos<total;pos+=12){
  const seed=start+pos%measured,shift=pos%cfg.binaries.length;
  let order=cfg.binaries.slice(shift).concat(cfg.binaries.slice(0,shift));
  if(Math.floor(pos/cfg.binaries.length)%2)order.reverse();
  for(const binary of order){
   if(!/^[a-z0-9-]+$/.test(binary))throw Error('invalid binary');
   let result=await tools.exec_command({cmd:`exec ${clean}${fixed}${dir}/${binary} < ${root}/tools/in/${String(seed).padStart(4,'0')}.txt > /dev/null`,yield_time_ms:10000,max_output_tokens:5000});
   let output=result.output;
   while(result.session_id){
    result=await tools.write_stdin({session_id:result.session_id,chars:'',yield_time_ms:1000,max_output_tokens:5000});output+=result.output;
   }
   const vals={};
   for(const m of output.matchAll(/^([A-Za-z_][A-Za-z_0-9]*) = ([-+0-9.eE]+)$/gm))vals[m[1]]=Number(m[2]);
   if(result.exit_code || !((cfg.sim?'sim_moves':'end_sec') in vals) || (cfg.sim && !('sim_moves' in vals)))throw Error(JSON.stringify({seed,binary,result,output}));
   if(pos<measured) {
    rows.push({binary,seed,lane:slot,returncode:result.exit_code,...vals});
    store('astra_design_progress',{label:cfg.label,done:rows.length,total:measured*cfg.binaries.length});
    if(rows.length%128===0)notify(`${cfg.label}: ${rows.length}/${measured*cfg.binaries.length} 実行完了`);
   }
  }
 }
})());
const results=await Promise.allSettled(tasks);
for(const r of results)if(r.status==='rejected')throw r.reason;
rows.sort((a,b)=>a.seed-b.seed||a.binary.localeCompare(b.binary));
const mean=v=>v.reduce((a,b)=>a+b,0)/v.length;
const columns=Array.from(new Set(rows.flatMap(r=>Object.keys(r))));
const summary={config:{...cfg,jobs:12,driver:'tools.exec_command, no resident OS controller'},variants:{},compare:{}};
for(const b of cfg.binaries){
 const rr=rows.filter(r=>r.binary===b),v={};
 for(const k of columns.filter(k=>!['binary','seed','lane'].includes(k))){
  const values=rr.filter(r=>k in r).map(r=>r[k]);if(values.length)v[k]={mean:mean(values),min:Math.min(...values),max:Math.max(...values)};
 }
 summary.variants[b]=v;
}
const baseline=new Map(rows.filter(r=>r.binary===cfg.binaries[0]).map(r=>[r.seed,r]));
for(const b of cfg.binaries.slice(1)){
 const v={};
 for(const metric of ['anneal_cost','sim_moves','total_moves','anneal_iters','gobj_after']){
  const pp=rows.filter(r=>r.binary===b&&metric in r).map(r=>[r[metric],baseline.get(r.seed)[metric]]);if(!pp.length)continue;
  const d=pp.map(([x,y])=>100*Math.log(x/y)),mu=mean(d);
  v[metric]={n:pp.length,log_pct:mu,se_pct:Math.sqrt(mean(d.map(x=>(x-mu)**2))/(d.length-1)),win:pp.filter(([x,y])=>x<y).length,tie:pp.filter(([x,y])=>x===y).length,loss:pp.filter(([x,y])=>x>y).length,delta:mean(pp.map(([x,y])=>x-y))};
 }
 summary.compare[b]=v;
}
const csv=columns.join(',')+'\n'+rows.map(r=>columns.map(k=>r[k]??'').join(',')).join('\n')+'\n';
for(const [file,body] of [[cfg.label+'.csv',csv],[cfg.label+'.json',JSON.stringify(summary,null,2)+'\n']]){
 const patch='*** Begin Patch\n*** Add File: '+dir+'/'+file+'\n'+body.trimEnd().split('\n').map(x=>'+'+x).join('\n')+'\n*** End Patch';
 text(await tools.apply_patch(patch));
}
store('astra_design_last',summary);
text(Object.fromEntries(Object.entries(summary.compare).map(([b,v])=>[b,{
 cost:v.anneal_cost?[v.anneal_cost.log_pct,v.anneal_cost.se_pct]:null,
 moves:v.sim_moves?[v.sim_moves.log_pct,v.sim_moves.se_pct]:null,
 wdl:v.sim_moves?[v.sim_moves.win,v.sim_moves.tie,v.sim_moves.loss]:null,
 iters:v.anneal_iters?.log_pct
}])));
