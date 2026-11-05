"""Fit a small deterministic policy using only pre-search observations."""
from pathlib import Path
import json
import numpy as np

p = Path(__file__).parent
a = np.load(p/'observations.npy').reshape(-1,3,19)
assert np.all(a[:,:,3] == np.arange(3))
# The first baseline request alone pays init_adaptive; never learn that as a budget saving.
a = a[a[:,0,2] > 0]
seed = a[:,0,0].astype(int)
X = a[:,0,[4,5,6,7,8,9,11]]
names = ['raw','ordinary','holes','generic','depth','fillers','gap']
g = np.column_stack([np.zeros(len(a)), a[:,:,15]])
t = np.column_stack([np.zeros(len(a)), a[:,:,17]-a[:,:,16]])
train = seed < 100
test = ~train
cuts = [[5,7,9,11,13,15,18], [4,6,8,10,12,14,17], [0,3,6,9,12,15,18],
        [5,8,11,14,17,20,25], [0,1,2,3,4,6], [0,1,2,3], [0.01,.1,.25,.5,1,2]]
policies=[]

def tree(mask, u, depth):
    values=u[mask].sum(axis=0)
    action=int(np.argmax(values))
    out={'action':action,'n':int(mask.sum())}
    if not depth:return out
    best=values[action];split=None
    for j, thresholds in enumerate(cuts):
        for threshold in thresholds:
            left=mask & (X[:,j]<=threshold);nl=left.sum()
            if nl<4000 or mask.sum()-nl<4000:continue
            lv=u[left].sum(axis=0);rv=values-lv
            value=lv.max()+rv.max()
            if value>best+0.05:
                best=value;split=(j,threshold,left)
    if split is not None:
        j,threshold,left=split
        out.update(feature=names[j],threshold=threshold,
                   left=tree(left,u,depth-1),right=tree(mask & ~left,u,depth-1))
    return out

def predict(node,mask,result):
    if 'feature' not in node:result[mask]=node['action'];return
    left=mask & (X[:,names.index(node['feature'])]<=node['threshold'])
    predict(node['left'],left,result);predict(node['right'],mask & ~left,result)

def describe(d,indent=''):
    if 'feature' not in d:print(indent+'action '+str(d['action'])+' n='+str(d['n']));return
    print(indent+d['feature']+' <= '+str(d['threshold']))
    describe(d['left'],indent+'  ');print(indent+'else');describe(d['right'],indent+'  ')

for price in [0,20,40,60,80,100,120,160,200,300]:
    u=g-price*t
    policy=tree(train,u,3)
    action=np.zeros(len(a),dtype=int);predict(policy,np.ones(len(a),dtype=bool),action)
    gain=g[np.arange(len(a)),action];time=t[np.arange(len(a)),action]
    print('\nPRICE',price)
    results={}
    for title,mask in [('train',train),('test',test),('all',train|test)]:
        gs=np.bincount(seed[mask],weights=gain[mask])[np.unique(seed[mask])]/2
        ts=np.bincount(seed[mask],weights=time[mask])[np.unique(seed[mask])]/2
        z={'gain_case':float(gs.mean()),'gain_se':float(gs.std(ddof=1)/len(gs)**.5),
           'seconds_case':float(ts.mean()),'counts':np.bincount(action[mask],minlength=4).tolist()}
        results[title]=z;print(title,z)
    describe(policy)
    policies.append({'price':price,'policy':policy,'results':results})
(p/'policies.json').write_text(json.dumps(policies,indent=2)+'\n')

# Hindsight chooses using the observed outcomes. It is a diagnostic, not an online policy.
print('\nHINDSIGHT')
for price in [40,80,120,200,400]:
    action=np.argmax(g-price*t,axis=1)
    print(price,'gain/case',g[np.arange(len(a)),action].sum()/400,
          'seconds/case',t[np.arange(len(a)),action].sum()/400)
