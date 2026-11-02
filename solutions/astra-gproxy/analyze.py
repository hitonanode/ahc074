"""割り当て終了時の状態から特徴を作る。入力内中心化、入力単位の検証。"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent

def mean_se(x):
    x = np.asarray(x)
    return float(x.mean()), float(x.std(ddof=1)/len(x)**.5)

def corr(x,y):
    return float(np.corrcoef(x,y)[0,1]) if np.std(x)>1e-12 and np.std(y)>1e-12 else 0.

def features(r):
    raw = r['raw']
    A = raw['A']
    hm = raw['HM'][0]
    handles = [j for j in range(63) if (hm>>j)&1]
    ab = np.array([[(a>>j)&1 for j in handles] for a in A],dtype=float)
    valid = np.array(raw['VALID']).reshape(-1,3)
    sel = np.array(raw['SELECT']).reshape(-1,2)
    hd = np.abs(ab[sel[:,0]]-ab[sel[:,1]])
    rel = {(int(u),int(v)):c/720 for u,v,c in valid}
    gc = np.array([rel[tuple(uv)] for uv in sel])
    dist = np.array([(A[u]^A[v]).bit_count() for u,v in sel])
    hs = hd.sum(axis=0)
    bias = abs(ab.sum(axis=0)-128)
    pairs_ones = (ab[sel[:,0]]+ab[sel[:,1]])*(1-hd)
    selected_set = set(map(tuple,sel))
    hdn = hd.sum(axis=1)
    f = dict(gobj=r['stats']['gobj_after'], hd=hdn.mean(), gc=gc.mean(), dist=dist.mean(),
             hd2=np.mean(hdn**2), gc2=np.mean(gc**2), hdgc=np.mean(hdn*gc),
             hd_sd=hdn.std(), gc_sd=gc.std(), hd_min=hdn.min(), hd_max=hdn.max(),
             hdiff_sd=hs.std(), hdiff2=np.mean(hs**2), hdiff_min=hs.min(), hdiff_max=hs.max(),
             hdiff_bias=np.mean(hs*bias), hdiff_bias2=np.mean(hs*bias**2),
             bias_abs=bias.mean(), bias2=np.mean(bias**2), bias_max=bias.max())
    for a,b in [(0,5),(5,10),(10,15),(15,20),(20,25)]:
        f[f'hdiff_q{a//5}'] = np.sort(hs)[a:b].mean()
    # Cheap potential for a rank-dependent cost: sort small conflict counts first.
    rank=np.arange(len(hs))/max(1,len(hs)-1)
    f['hdiff_rank']=np.mean(np.sort(hs)*rank)
    f['hdiff_sqrt']=np.mean(np.sqrt(hs))
    for t in (10,20,30,40,60,100):
        f[f'hdiff_sat{t}']=np.mean(hs/(hs+t))
        f[f'hdiff_harm{t}']=np.mean(hs*(hs+t)/(2*hs+t))
    for theta in (0,1,2):
        z=hs-theta*bias
        f[f'biased_rank{theta}']=np.mean(np.sort(z)*rank)
    deg=np.bincount(valid[:,:2].ravel(),minlength=256)
    vhd=np.array([((A[u]^A[v])&hm).bit_count() for u,v,_ in valid])
    vg=valid[:,2]/720
    vk=.5*vhd+vg+.04*np.array([(A[u]^A[v]).bit_count() for u,v,_ in valid])
    f.update(compatible=len(valid),degree0=np.sum(deg==0),degree1=np.sum(deg==1),degree2=np.sum(deg<=2),
             degree_sd=deg.std(),degree_log=np.mean(np.log1p(deg)),
             valid_hd=vhd.mean(),valid_gc=vg.mean())
    for t in (7,8,9,10,11,12):
        f[f'valid_below{t}']=sum(vk<t)
    best=np.full(256,20.)
    for (u,v,_),k in zip(valid,vk):
        best[u]=min(best[u],k)
        best[v]=min(best[v],k)
    for count in (100,142,180,220,256):
        f[f'vertex_best{count}']=np.sort(best)[:count].mean()
    used=set()
    total=0.
    count=0
    for i in np.argsort(vk,kind='stable'):
        u,v,_=valid[i]
        if u in used or v in used: continue
        used.update((u,v)); total+=vk[i];count+=1
        if count in (40,60,71,80,90,100): f[f'match{count}']=total/count
    f['match_count']=count
    for count in (40,60,71,80,90,100): f.setdefault(f'match{count}',20.)
    # Signed joint colors of the selected papers, with pairs counted twice.
    covered=set(sel.ravel())
    singles=[i for i in range(256) if i not in covered]
    unit=np.concatenate((ab[singles]*2-1,(ab[sel[:,0]]+ab[sel[:,1]]-1)*2))
    gram=unit.T@unit/256
    off=gram[np.triu_indices(len(handles),1)]
    f['unit_corr_abs']=np.mean(abs(off))
    f['unit_corr2']=np.mean(off**2)
    f['unit_pca']=np.linalg.eigvalsh(gram)[-1]
    f['equal_bias']=np.mean(abs(pairs_ones.sum(axis=0)-(len(sel)-hs)))
    f['equal_bias2']=np.mean((pairs_ones.sum(axis=0)-(len(sel)-hs))**2)
    # Comparison structure: each of the 15 edges has >=1 windows.
    sizes=np.array([m.bit_count() for m in raw['MASK']])
    f['edge2']=np.mean(sizes**2)
    f['edge_max']=sizes.max()
    f['edge_single']=np.sum(sizes==1)
    sheets=np.zeros(6)
    z=0
    for a in range(6):
        for b in range(a+1,6):
            sheets[a]+=sizes[z];sheets[b]+=sizes[z];z+=1
    f['sheet2']=np.mean(sheets**2)
    # Final state diagnostics are outcomes, never predictors.
    uu=np.array(raw['UNIT']).reshape(-1,3)
    fp=uu[uu[:,1]>=0]
    final_set={tuple(sorted((a,b))) for a,b,c in fp}
    out={k:r['stats'][k] for k in ('model_cost','model_col','model_hole','model_gc')}
    if 'sim_moves' in r['stats']: out['sim_moves']=r['stats']['sim_moves']
    out['kept_pairs']=len(selected_set&final_set)
    out['final_hd']=np.mean([((A[a]^A[b])&hm).bit_count() for a,b,c in fp])
    out['final_dist']=np.mean([(A[a]^A[b]).bit_count() for a,b,c in fp])
    out['final_hdiff_sd']=np.std(np.abs(ab[fp[:,0]]-ab[fp[:,1]]).sum(axis=0))
    for k,v in f.items():
        assert np.isfinite(v),(k,v)
    return f,out

def center(X, seeds):
    out=np.array(X,copy=True,dtype=float)
    for seed in np.unique(seeds): out[seeds==seed]-=out[seeds==seed].mean(axis=0)
    return out

def regress(X,y,train,test,alpha=0.):
    scale=X[train].std(axis=0)
    scale=np.where(scale>1e-12,scale,1.)
    a=X[train]/scale
    coef=np.linalg.solve(a.T@a+np.eye(a.shape[1])*alpha,a.T@y[train])/scale
    pred=X@coef
    return coef,pred

def main():
    p=argparse.ArgumentParser()
    p.add_argument('name',nargs='?',default='research')
    p.add_argument('--target',default='model_cost')
    args=p.parse_args()
    data=[json.loads(p.read_text()) for p in sorted((HERE/'data'/args.name).glob('[0-9][0-9][0-9][0-9]-*.json'))]
    data=[r for r in data if r.get('raw') and 'UNIT' in r['raw']]
    fs,ys=zip(*[features(r) for r in data])
    names=list(fs[0]); outs=[args.target]+[k for k in ys[0] if k!=args.target]
    seeds=np.array([r['seed'] for r in data]); ms=np.array([r['map_seed'] for r in data])
    X=center(np.array([[f[k] for k in names] for f in fs]),seeds)
    Y=center(np.array([[y[k] for k in outs] for y in ys]),seeds)
    unique=np.unique(seeds)
    train=seeds<56; test=seeds>=56
    if sum(test)<24: train=seeds%2==0;test=~train
    rows=[]
    for j,k in enumerate(names):
        per=[corr(X[seeds==s,j],Y[seeds==s,0]) for s in unique]
        row=dict(feature=k,pooled=corr(X[:,j],Y[:,0]),train=corr(X[train,j],Y[train,0]),
                 test=corr(X[test,j],Y[test,0]),mean_corr=mean_se(per)[0],se_corr=mean_se(per)[1])
        for i,out in enumerate(outs[1:],1): row[out]=corr(X[:,j],Y[:,i])
        rows.append(row)
    rows.sort(key=lambda r:-abs(r['train']))
    path=HERE/'data'/args.name/'features.tsv'
    with path.open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['seed','map_seed']+names+outs)
        for r,x,y in zip(data,fs,ys): w.writerow([r['seed'],r['map_seed']]+[x[k] for k in names]+[y[k] for k in outs])
    print('n=',len(data),'inputs=',len(unique),'train/test=',sum(train),sum(test))
    print('within sd model',np.std(Y[:,0]),'kept pairs',np.mean([r['kept_pairs'] for r in ys]))
    print('feature\ttrain\ttest\tmean_corr\tse\tcol\thole\tgc')
    for r in rows:
        print(r['feature'],*[f'{r[k]:.4f}' for k in ('train','test','mean_corr','se_corr','model_col','model_hole','model_gc')],sep='\t')
    groups=[['gobj'],['hd','gc','dist'],['gobj','bias2'],['gobj','hdiff_sd'],
            ['gobj','bias2','hdiff_sd'],['hd','gc','dist','bias2','hdiff_sd'],
            ['gobj','degree_log'],['gobj','bias2','hdiff_sd','degree_log'],
            ['gobj','unit_corr2'],['gobj','bias2','hdiff_sd','unit_corr2']]
    results=[]
    for group in groups:
        ids=[names.index(k) for k in group]
        b,pred=regress(X[:,ids],Y[:,0],train,test,1.)
        result=dict(features=group,coef=list(b),train_corr=corr(pred[train],Y[train,0]),
                    test_corr=corr(pred[test],Y[test,0]),
                    test_rmse=float(np.sqrt(np.mean((pred[test]-Y[test,0])**2))))
        results.append(result)
        print('REG',json.dumps(result))
    # Leave-one-input-out CV evaluates a predeclared small regression without using its test input.
    for group in groups:
        ids=[names.index(k) for k in group]
        pred=np.zeros(len(seeds))
        for s in unique:
            b,z=regress(X[:,ids],Y[:,0],seeds!=s,seeds==s,1.)
            pred[seeds==s]=z[seeds==s]
        per=[corr(pred[seeds==s],Y[seeds==s,0]) for s in unique]
        selected=[Y[seeds==s,0][np.argmin(pred[seeds==s])] for s in unique]
        print('CV',group,'pooled',corr(pred,Y[:,0]),'mean_r/se',mean_se(per),'selection/se',mean_se(selected))
    (HERE/'data'/args.name/f'analysis-{args.target}.json').write_text(json.dumps(dict(n=len(data),inputs=len(unique),
        correlations=rows,regressions=results),indent=2))

if __name__=='__main__': main()
