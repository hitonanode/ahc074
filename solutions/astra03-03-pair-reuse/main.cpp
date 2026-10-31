#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <queue>
#include <random>
#include <set>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
#include <bitset>
#include <deque>
#include <limits>
#include <climits>
#include <cstring>
using namespace std;using U=uint64_t;int pc(U x){return __builtin_popcountll(x);}struct Paper{U m,b;int bank=-1;};struct Cand{U m,b;vector<int>rows;int w,bank,col;};struct Entry{int gain,id,version;bool operator<(const Entry&o)const{return gain<o.gain;}};
int main(int argc,char**argv){int H=argc>1?atoi(argv[1]):24,seed=argc>2?atoi(argv[2]):1,Q=argc>3?atoi(argv[3]):1024;mt19937_64 rng(seed);U DM=~((1ULL<<H)-1);int D=64-H,M=192-D-1;int N_,K_,P_,R_;cin>>N_>>K_>>P_>>R_;vector<U>A(256);for(U &x:A){string s_;cin>>s_;x=0;for(int j=0;j<64;j++)if(s_[j]=='1')x|=1ULL<<j;}vector<U>originalA=A;assert(set<U>(A.begin(),A.end()).size()==256);U flip=0;for(int j=H;j<64;j++){int ones=0;for(U x:A)ones+=(x>>j)&1;if(ones>128)flip|=1ULL<<j;}for(U&x:A)x^=flip;auto start=chrono::steady_clock::now();vector<Cand>cs;vector<vector<int>>cids(2*H);vector<int>bankSize(H);vector<array<int,2>>cap(H);for(int j=0;j<H;j++){int n=M/H+(j>=H-M%H);bankSize[j]=n;cap[j]={n/2,n-n/2};}
auto val=[&](U m,U b,int j){return 2*pc(b&DM)+pc(m&~DM)-(bankSize[j]+3);};auto pval=[&](Paper pp){return val(pp.m,pp.b,pp.bank);};

vector<vector<double>>F(D+1,vector<double>(D+1));mt19937_64 frng(918726);for(int nz=0;nz<=D;nz++)for(int no=0;no+nz<=D;no++){if(!nz&&!no)continue;double sum=0;for(int rep=0;rep<512;rep++){vector<int>perm(D);iota(perm.begin(),perm.end(),0);shuffle(perm.begin(),perm.end(),frng);U z=0,o=0;for(int i=0;i<nz;i++)z|=1ULL<<perm[i];for(int i=nz;i<nz+no;i++)o|=1ULL<<perm[i];int b=rep%4?D-int(frng()%(D/3+1)):int(frng()%(D+1));int t=z?64-__builtin_clzll(z):0;U preB=b==64?~0ULL:((1ULL<<b)-1);int best=999;if(!(z&~preB))best=pc(o&preB);int c=max(b,t);for(int k=0;k<=t;k++){U pre=k==64?~0ULL:((1ULL<<k)-1);int zm=pc(z&~pre),om=pc(o&pre),fc=k+zm,fm=(fc!=c),helper=0;if(c==D&&fm&&om==0){helper=1;if(fc==D-1)fm=0;}best=min(best,(b<t)+zm+om+fm+helper);}sum+=best;}F[nz][no]=sum/512;}
vector<int>totOne(256);for(int v=0;v<256;v++)totOne[v]=pc(A[v]&DM);
auto quality=[&](U m,U b,int bank,int v){int one=totOne[v],zero=D-one;int ho=one-pc(b&DM),hz=zero-pc(m&~b&DM);assert(ho>=0&&hz>=0);double gain=F[zero][one]-F[hz][ho]+0.5*pc(m&~DM)-0.5*(bankSize[bank]+3);return int(lround(32*gain));};
for(int j=0;j<H;j++){U allowed=DM|((1ULL<<(j+1))-1);set<pair<U,U>>seen;auto add=[&](U m,U b){b&=m;if(!seen.insert({m,b}).second)return;Cand c{m,b,{},val(m,b,j),j,int(b>>j&1)};for(int v=0;v<256;v++)if(!((A[v]^b)&m))c.rows.push_back(v);cids[2*j+c.col].push_back(cs.size());cs.push_back(move(c));};for(U a:A)add(allowed,a);for(int p=0;p<256;p++)for(int q=0;q<p;q++)if(!((A[p]^A[q])>>j&1))add(allowed&~(A[p]^A[q]),A[p]);
for(int p=0;p<256;p++){vector<pair<int,int>>near;for(int q=0;q<256;q++)if(p!=q&&!((A[p]^A[q])>>j&1)){U m=allowed&~(A[p]^A[q]);int score=8*pc(m&A[p]&DM)+4*pc(m&~DM)+pc(m&~A[p]&DM);near.push_back({score,q});}sort(near.begin(),near.end(),greater<pair<int,int>>());for(int tr=0;tr<0;tr++){int q=near[rng()%min<int>(32,near.size())].second;U m=allowed&~(A[p]^A[q]);vector<int>used{p,q};for(int depth=0;depth<5;depth++){add(m,A[p]);array<pair<int,int>,3> best;for(auto&x:best)x={-1,-1};for(int r=0;r<256;r++)if(!((A[p]^A[r])>>j&1)&&find(used.begin(),used.end(),r)==used.end()){U mm=m&~(A[p]^A[r]);int score=8*pc(mm&A[p]&DM)+4*pc(mm&~DM)+pc(mm&~A[p]&DM);pair<int,int> v{score,r};for(int k=0;k<3;k++)if(v>best[k])swap(v,best[k]);}int r=best[rng()%3].second;m&=~(A[p]^A[r]);used.push_back(r);}}}}
vector<int>covered(256);int ver=0;auto evaluate=[&](int id){auto&c=cs[id];int gain=0;for(int v:c.rows)gain+=max(0,quality(c.m,c.b,c.bank,v)-covered[v]);return Entry{gain,id,ver};};priority_queue<Entry>heap;for(int id=0;id<(int)cs.size();id++)heap.push(evaluate(id));vector<vector<Paper>>chosen(2*H);int ng=0;for(int t=0;t<M;t++){Entry e;while(true){e=heap.top();heap.pop();auto&cc=cs[e.id];if(!cap[cc.bank][cc.col])continue;if(e.version==ver)break;heap.push(evaluate(e.id));}auto&c=cs[e.id];cap[c.bank][c.col]--;chosen[2*c.bank+c.col].push_back({c.m,c.b,c.bank});for(int v:c.rows)covered[v]=max(covered[v],quality(c.m,c.b,c.bank,v));ng+=e.gain;ver++;heap.push(evaluate(e.id));}
for(int outer=0;outer<1;outer++){for(int pass=0;pass<3;pass++){int done=0;for(int bucket=0;bucket<2*H;bucket++)for(int slot=0;slot<(int)chosen[bucket].size();slot++){vector<int>bc(256);for(int bb=0;bb<2*H;bb++)for(int ss=0;ss<(int)chosen[bb].size();ss++){if(bb==bucket&&ss==slot)continue;auto pp=chosen[bb][ss];int w=pval(pp);for(int v=0;v<256;v++)if(!((A[v]^pp.b)&pp.m))bc[v]=max(bc[v],quality(pp.m,pp.b,pp.bank,v));}auto old=chosen[bucket][slot];int oldw=pval(old),gain=0,bestid=-1;for(int v=0;v<256;v++)if(!((A[v]^old.b)&old.m))gain+=max(0,quality(old.m,old.b,old.bank,v)-bc[v]);for(int id:cids[bucket]){auto&c=cs[id];int gg=0;for(int v:c.rows)gg+=max(0,quality(c.m,c.b,c.bank,v)-bc[v]);if(gg>gain){gain=gg;bestid=id;}}if(bestid>=0){auto&c=cs[bestid];chosen[bucket][slot]={c.m,c.b,c.bank};done++;}}if(!done)break;}
if(outer==0)break;int c0[64]={},c1[64]={};for(int v=0;v<256;v++){int score=-100,sz=-1;U mask=0;for(auto&bucket:chosen)for(auto pp:bucket)if(!((A[v]^pp.b)&pp.m)){int w=pval(pp),z=pc(pp.m&DM);if(w>score||(w==score&&z>sz)){score=w;sz=z;mask=pp.m;}}for(int j=H;j<64;j++)if(!(mask>>j&1)){if(A[v]>>j&1)c1[j]++;else c0[j]++;}}U delta=0;for(int j=H;j<64;j++)if(c1[j]>c0[j])delta|=1ULL<<j;if(!delta)break;flip^=delta;for(U&x:A)x^=delta;for(auto&c:cs){c.b^=c.m&delta;c.w=val(c.m,c.b,c.bank);}for(auto&bucket:chosen)for(auto&pp:bucket)pp.b^=delta&pp.m;}

for(int pass=0;pass<2;pass++){int changes=0;for(int j=0;j<H;j++)for(int co=0;co<2;co++){int bucket=2*j+co;for(int slot=(int)chosen[bucket].size()-1;slot>=0;slot--){Paper old=chosen[bucket][slot];chosen[bucket].erase(chosen[bucket].begin()+slot);vector<int>bc(256);for(auto&list:chosen)for(auto pp:list)for(int v=0;v<256;v++)if(!((A[v]^pp.b)&pp.m))bc[v]=max(bc[v],quality(pp.m,pp.b,pp.bank,v));int bestGain=0,bestid=-1;for(int v=0;v<256;v++)if(!((A[v]^old.b)&old.m))bestGain+=max(0,quality(old.m,old.b,j,v)-bc[v]);for(int c=0;c<2;c++){if(chosen[bucket].empty()&&c!=co)continue;for(int id:cids[2*j+c]){auto&cc=cs[id];int g=0;for(int v:cc.rows)g+=max(0,quality(cc.m,cc.b,j,v)-bc[v]);if(g>bestGain){bestGain=g;bestid=id;}}}if(bestid<0)chosen[bucket].insert(chosen[bucket].begin()+slot,old);else{auto&cc=cs[bestid];Paper np{cc.m,cc.b,j};if(cc.col==co)chosen[bucket].insert(chosen[bucket].begin()+slot,np);else chosen[2*j+cc.col].push_back(np);changes++;}}}if(!changes)break;}
vector<Paper>p;for(int j=H;j<64;j++)p.push_back({1ULL<<j,0,-1});int bg=p.size();p.push_back({DM,DM,-1});for(int j=0;j<H;j++)for(int z=0;z<(int)max(chosen[2*j].size(),chosen[2*j+1].size());z++)for(int c=0;c<2;c++)if(z<(int)chosen[2*j+c].size())p.push_back(chosen[2*j+c][z]);while(p.size()<192)p.push_back({0,0,-1});double designtime=chrono::duration<double>(chrono::steady_clock::now()-start).count();
{string out_;for(int k=0;k<192;k++){for(int j=0;j<64;j++)out_+=(p[k].m>>j&1)?char('0'+((p[k].b^(p[k].m&flip))>>j&1)):'.';out_+='\n';}cout<<out_<<flush;}
vector<int>ord(192);iota(ord.begin(),ord.end(),0);auto render=[&](const vector<int>&o){U mask=0,x=0;for(int k:o){x|=p[k].b&~mask;mask|=p[k].m;}return x;};int baselineSum=0;int active=-1,controlActive=-1,total=0,dataops=0,fetchops=0,handleops=0,removeops=0,promoteops=0,basecount=0;vector<int>hist(100);int last=-1;for(int t=0;t<Q;t++){int a;if(!(cin>>a)||a<0)return 0;baselineSum+=last<0?pc(originalA[a]):pc(originalA[a]^originalA[last]);last=a;U target=A[a];int steps=0;vector<pair<int,int>>operations;auto act=[&](int k,int d){U cover=0;bool found=false;int i=0;for(;i<192;i++){int x=ord[i];if(x==k){assert(p[k].m&~cover);found=true;break;}cover|=p[x].m;}assert(found);ord.erase(ord.begin()+i);ord.insert(ord.begin()+d,k);steps++;operations.push_back({k,d});};

auto placeAfter=[&](int k,int anchor){int d=0,after=-1;for(int x:ord)if(x!=k){if(x==anchor)after=d+1;d++;}assert(after>=0);act(k,after);};
auto retire=[&](int k){int j=p[k].bank;if(((p[k].b^target)>>j)&1){int next=-1;for(int x:ord)if(x!=k&&p[x].bank==j){next=x;break;}assert(next>=0&&(((p[next].b^p[k].b)>>j)&1));placeAfter(k,next);return;}int d=0,at=-1;for(int x:ord)if(x!=k){if(at<0&&p[x].bank==j)at=d;d++;}assert(at>=0);act(k,at);};
auto flipHead=[&](int k){int next=-1;for(int x:ord)if(x!=k&&p[x].bank==p[k].bank){next=x;break;}assert(next>=0);assert(((p[next].b^p[k].b)>>p[k].bank)&1);placeAfter(k,next);};

int prevControl=controlActive;if(active>=0){retire(active);removeops++;active=-1;}vector<int>reuseSnapshot=ord;auto reuseOps=operations;if(controlActive>=0){retire(controlActive);removeops++;controlActive=-1;}
U x=render(ord);int he=pc((x^target)&~DM);vector<U>pref(1,0);vector<int>leaves;int bcut=0;for(int k:ord){if(k==bg)bcut=leaves.size();if(k<bg){leaves.push_back(k);pref.push_back(pref.back()|p[k].m);}}

struct BP{int cost,k,t;bool keep;};auto baseplan=[&](U holes){U z=holes&~target,o=holes&target;int t=0;for(int i=0;i<D;i++)if(z&p[leaves[i]].m)t=i+1;BP best{999,bcut,t,true};if(!(z&~pref[bcut]))best.cost=pc(o&pref[bcut]);int c=max(bcut,t);for(int k=0;k<=t;k++){int zm=pc(z&~pref[k]),om=pc(o&pref[k]);int fc=k+zm;int fm=(fc!=c),helper=0;if(c==D&&fm&&om==0){helper=1;if(fc==D-1)fm=0;}int cost=(bcut<t)+zm+om+fm+helper;if(cost<best.cost)best={cost,k,t,false};}return best;};


U holes=DM;BP bp=baseplan(holes);double best=bp.cost+he;int bid=-1,cid=-1;int rank[64]={};vector<int>rr(192);for(int k:ord)if(p[k].bank>=0)rr[k]=rank[p[k].bank]++;
auto assess=[&](int main){U mm=main<0?0:p[main].m;U hs=DM&~mm;auto plan=baseplan(hs);double fixed=plan.cost+(main<0?0:rr[main]+1.7);double cost=fixed+he-pc((x^target)&mm&~DM);if(cost<best){best=cost;bid=main;cid=-1;bp=plan;holes=hs;}
for(int c:ord)if(p[c].bank>=0&&(main<0||p[c].bank!=p[main].bank)){U cm=p[c].m&~DM;if((p[c].b^target)&cm&~mm)continue;double co=fixed+rr[c]+1.7+he-pc((x^target)&(mm|cm)&~DM);if(c==prevControl&&(main<0||!(p[c].m>>p[main].bank&1)))co=fixed-0.3+he-pc((x^target)&(mm|cm)&~DM);if(co<best){best=co;bid=main;cid=c;bp=plan;holes=hs;}}};
assess(-1);for(int k:ord)if(p[k].bank>=0&&!((p[k].b^target)&p[k].m))assess(k);

if(bid<0)basecount++;bool reuseControl=cid>=0&&cid==prevControl&&(bid<0||!(p[cid].m>>p[bid].bank&1));if(reuseControl){ord=reuseSnapshot;operations=reuseOps;steps--;removeops--;controlActive=cid;}

int beforedata=dataops;U o=holes&target,z=holes&~target;
if(!bp.keep){if(bcut<bp.t){act(bg,bp.t);dataops++;}U movez=z&~pref[bp.k];int fc=bp.k+pc(movez);while(movez){int j=__builtin_ctzll(movez);movez&=movez-1;act(j-H,0);dataops++;}
int posbg=find(ord.begin(),ord.end(),bg)-ord.begin();if(posbg==D&&fc<D){U opts=o&pref[bp.k];if(!opts)opts=DM&~pref[bp.k]&~z;assert(opts);int j=__builtin_ctzll(opts),helper=j-H;int orig=find(leaves.begin(),leaves.end(),helper)-leaves.begin();act(helper,D);dataops++;if(orig<bp.k)fc--;}
posbg=find(ord.begin(),ord.end(),bg)-ord.begin();if(posbg!=fc){act(bg,fc);dataops++;}}
while(true){int bad=-1;for(int k:ord){if(k==bg)break;if(k<bg&&(p[k].m&o)){bad=k;break;}}if(bad<0)break;act(bad,D);dataops++;}assert(dataops-beforedata==bp.cost);


vector<int>picks;if(bid>=0)picks.push_back(bid);if(cid>=0&&!reuseControl)picks.push_back(cid);sort(picks.begin(),picks.end(),[&](int a,int b){return p[a].bank<p[b].bank;});for(int id:picks){int j=p[id].bank,storedOpp=-1;while(true){int head=-1;for(int k:ord)if(p[k].bank==j){head=k;break;}if(head==id)break;int co=(p[head].b>>j)&1,goal=(p[id].b>>j)&1;int anchor=(co!=goal||storedOpp<0)?id:storedOpp;placeAfter(head,anchor);if(co!=goal)storedOpp=head;fetchops++;}if(id==bid){act(id,0);active=id;}else{act(id,D+1+(active>=0));controlActive=id;}promoteops++;}
for(int j=0;j<H;j++)if((render(ord)^target)>>j&1){int owner=-1;for(int k:ord)if(p[k].m>>j&1){owner=k;break;}flipHead(owner);handleops++;}
assert(render(ord)==target);U realMask=0,realX=0;for(int k:ord){realX|=(p[k].b^(p[k].m&flip))&~realMask;realMask|=p[k].m;}assert(realMask==~0ULL);assert(realX==originalA[a]);assert(steps<=384);total+=steps;hist[steps]++;assert((int)operations.size()==steps);{string out_=to_string(operations.size())+"\n";for(auto[k_,d_]:operations)out_+=to_string(k_)+" "+to_string(d_)+"\n";cout<<out_<<flush;}}
int mx=0;for(int i=0;i<100;i++)if(hist[i])mx=i;cerr<<"H "<<H<<" seed "<<seed<<" candidates "<<cs.size()<<" bestcov "<<double(ng)/256<<" avg "<<double(total)/Q<<" design_s "<<designtime<<" total_s "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<" components "<<double(dataops)/Q<<","<<double(fetchops)/Q<<","<<double(handleops)/Q<<","<<double(removeops)/Q<<","<<double(promoteops)/Q<<" baseline_avg "<<double(baselineSum)/Q<<" unused_template "<<basecount<<" max "<<mx<<endl;}
