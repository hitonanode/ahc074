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
int main(int argc,char**argv){int H=argc>1?atoi(argv[1]):38,seed=argc>2?atoi(argv[2]):1,Q=argc>3?atoi(argv[3]):1024;int accessUnit=argc>5?atoi(argv[5]):16;double cw=argc>6?atof(argv[6]):0.35;mt19937_64 rng(seed);U DM=~((1ULL<<H)-1);int D=64-H,M=192-D-1;int N_,K_,P_,R_;cin>>N_>>K_>>P_>>R_;vector<U>A(256);for(U &x:A){string s_;cin>>s_;x=0;for(int j=0;j<64;j++)if(s_[j]=='1')x|=1ULL<<j;}vector<U>originalA=A;assert(set<U>(A.begin(),A.end()).size()==256);U flip=0;for(int j=H;j<64;j++){int ones=0;for(U x:A)ones+=(x>>j)&1;if(ones>128)flip|=1ULL<<j;}for(U&x:A)x^=flip;auto start=chrono::steady_clock::now();vector<Cand>cs;vector<vector<int>>cids(2*H);vector<int>bankSize(H);vector<array<int,2>>cap(H);for(int j=0;j<H;j++){int n=2;bankSize[j]=n;cap[j]={1,1};}
auto val=[&](U m,U b,int j){return 2*pc(b&DM)+pc(m&~DM)-(bankSize[j]+3);};auto pval=[&](Paper pp){return val(pp.m,pp.b,pp.bank);};

vector<vector<double>>F(D+1,vector<double>(D+1));mt19937_64 frng(918726);for(int nz=0;nz<=D;nz++)for(int no=0;no+nz<=D;no++){if(!nz&&!no)continue;double sum=0;for(int rep=0;rep<512;rep++){vector<int>perm(D);iota(perm.begin(),perm.end(),0);shuffle(perm.begin(),perm.end(),frng);U z=0,o=0;for(int i=0;i<nz;i++)z|=1ULL<<perm[i];for(int i=nz;i<nz+no;i++)o|=1ULL<<perm[i];int b=rep%4?D-int(frng()%(D/3+1)):int(frng()%(D+1));int t=z?64-__builtin_clzll(z):0;U preB=b==64?~0ULL:((1ULL<<b)-1);int best=999;if(!(z&~preB))best=pc(o&preB);int c=max(b,t);for(int k=0;k<=t;k++){U pre=k==64?~0ULL:((1ULL<<k)-1);int zm=pc(z&~pre),om=pc(o&pre),fc=k+zm,fm=(fc!=c),helper=0;if(c==D&&fm&&om==0){helper=1;if(fc==D-1)fm=0;}best=min(best,(b<t)+zm+om+fm+helper);}sum+=best;}F[nz][no]=sum/512;}
vector<int>totOne(256);for(int v=0;v<256;v++)totOne[v]=pc(A[v]&DM);
auto quality=[&](U m,U b,int bank,int v){int one=totOne[v],zero=D-one;int ho=one-pc(b&DM),hz=zero-pc(m&~b&DM);assert(ho>=0&&hz>=0);double gain=F[zero][one]-F[hz][ho]+cw*pc(m&~DM)-(accessUnit*(bankSize[bank]-1)/32.0+2.0);return int(lround(32*gain));};
for(int j=0;j<H;j++){U allowed=DM|((1ULL<<(j+1))-1);set<pair<U,U>>seen;auto add=[&](U m,U b){b&=m;if(!seen.insert({m,b}).second)return;Cand c{m,b,{},val(m,b,j),j,int(b>>j&1)};for(int v=0;v<256;v++)if(!((A[v]^b)&m))c.rows.push_back(v);cids[2*j+c.col].push_back(cs.size());cs.push_back(move(c));};for(U a:A)add(allowed,a);for(int p=0;p<256;p++)for(int q=0;q<p;q++)if(!((A[p]^A[q])>>j&1))add(allowed&~(A[p]^A[q]),A[p]);
}

{
 vector<vector<pair<int,int>>>top(H*256);int limit=12;
 for(int id=0;id<(int)cs.size();id++){auto&c=cs[id];for(int v:c.rows){auto&ls=top[c.bank*256+v];ls.push_back({quality(c.m,c.b,c.bank,v),id});}}
 vector<bool>keep(cs.size());for(auto&ls:top){sort(ls.begin(),ls.end(),greater<pair<int,int>>());for(int i=0;i<(int)min<size_t>(limit,ls.size());i++)keep[ls[i].second]=true;}
 vector<Cand>filtered;for(auto&ls:cids)ls.clear();for(int i=0;i<(int)cs.size();i++)if(keep[i]){auto&c=cs[i];cids[2*c.bank+c.col].push_back(filtered.size());filtered.push_back(move(c));}cs=move(filtered);
}
vector<vector<int>>candidateQ(cs.size());for(int id=0;id<(int)cs.size();id++)for(int v:cs[id].rows)candidateQ[id].push_back(quality(cs[id].m,cs[id].b,cs[id].bank,v));
vector<int>covered(256);int ver=0;auto evaluate=[&](int id){auto&c=cs[id];int gain=0;for(int v:c.rows)gain+=max(0,quality(c.m,c.b,c.bank,v)-covered[v]);return Entry{gain,id,ver};};priority_queue<Entry>heap;for(int id=0;id<(int)cs.size();id++)heap.push(evaluate(id));vector<vector<Paper>>chosen(2*H);int ng=0;for(int t=0;t<2*H;t++){Entry e;while(true){e=heap.top();heap.pop();auto&cc=cs[e.id];if(!cap[cc.bank][cc.col])continue;if(e.version==ver)break;heap.push(evaluate(e.id));}auto&c=cs[e.id];cap[c.bank][c.col]--;chosen[2*c.bank+c.col].push_back({c.m,c.b,c.bank});for(int v:c.rows)covered[v]=max(covered[v],quality(c.m,c.b,c.bank,v));ng+=e.gain;ver++;heap.push(evaluate(e.id));}

vector<vector<int>>bankQ(H,vector<int>(256,-1000000));
for(auto&ls:chosen)for(auto pp:ls)for(int v=0;v<256;v++)if(!((A[v]^pp.b)&pp.m))bankQ[pp.bank][v]=max(bankQ[pp.bank][v],quality(pp.m,pp.b,pp.bank,v));
for(int num=2*H;num<M;num++){
 vector<vector<int>>other(H,vector<int>(256)),base(H,vector<int>(256));vector<int>penalty(H);
 for(int v=0;v<256;v++){
  int top=0,second=0,jj=-1;for(int j=0;j<H;j++){int q=bankQ[j][v];if(q>top){second=top;top=q;jj=j;}else second=max(second,q);}
  for(int j=0;j<H;j++){other[j][v]=j==jj?second:top;base[j][v]=max(other[j][v],bankQ[j][v]-accessUnit);penalty[j]+=base[j][v]-top;}
 }
 int bestId=-1,bestGain=INT_MIN;
 for(int id=0;id<(int)cs.size();id++){auto&c=cs[id];int j=c.bank;if(bankSize[j]>=16)continue;int gain=penalty[j];for(int i=0;i<(int)c.rows.size();i++){int v=c.rows[i];gain+=max(0,candidateQ[id][i]-accessUnit*(bankSize[j]-1)-base[j][v]);}if(gain>bestGain){bestGain=gain;bestId=id;}}
 auto&c=cs[bestId];int j=c.bank;bankSize[j]++;for(int v=0;v<256;v++)bankQ[j][v]-=accessUnit;
 chosen[2*j+c.col].push_back({c.m,c.b,j});for(int v:c.rows)bankQ[j][v]=max(bankQ[j][v],quality(c.m,c.b,j,v));
}
for(int outer=0;outer<1;outer++){for(int pass=0;pass<3;pass++){int done=0;for(int bucket=0;bucket<2*H;bucket++)for(int slot=0;slot<(int)chosen[bucket].size();slot++){vector<int>bc(256);for(int bb=0;bb<2*H;bb++)for(int ss=0;ss<(int)chosen[bb].size();ss++){if(bb==bucket&&ss==slot)continue;auto pp=chosen[bb][ss];int w=pval(pp);for(int v=0;v<256;v++)if(!((A[v]^pp.b)&pp.m))bc[v]=max(bc[v],quality(pp.m,pp.b,pp.bank,v));}auto old=chosen[bucket][slot];int oldw=pval(old),gain=0,bestid=-1;for(int v=0;v<256;v++)if(!((A[v]^old.b)&old.m))gain+=max(0,quality(old.m,old.b,old.bank,v)-bc[v]);for(int id:cids[bucket]){auto&c=cs[id];int gg=0;for(int v:c.rows)gg+=max(0,quality(c.m,c.b,c.bank,v)-bc[v]);if(gg>gain){gain=gg;bestid=id;}}if(bestid>=0){auto&c=cs[bestid];chosen[bucket][slot]={c.m,c.b,c.bank};done++;}}if(!done)break;}
if(outer==0)break;int c0[64]={},c1[64]={};for(int v=0;v<256;v++){int score=-100,sz=-1;U mask=0;for(auto&bucket:chosen)for(auto pp:bucket)if(!((A[v]^pp.b)&pp.m)){int w=pval(pp),z=pc(pp.m&DM);if(w>score||(w==score&&z>sz)){score=w;sz=z;mask=pp.m;}}for(int j=H;j<64;j++)if(!(mask>>j&1)){if(A[v]>>j&1)c1[j]++;else c0[j]++;}}U delta=0;for(int j=H;j<64;j++)if(c1[j]>c0[j])delta|=1ULL<<j;if(!delta)break;flip^=delta;for(U&x:A)x^=delta;for(auto&c:cs){c.b^=c.m&delta;c.w=val(c.m,c.b,c.bank);}for(auto&bucket:chosen)for(auto&pp:bucket)pp.b^=delta&pp.m;}

for(int pass=0;pass<2;pass++){int changes=0;for(int j=0;j<H;j++)for(int co=0;co<2;co++){int bucket=2*j+co;for(int slot=(int)chosen[bucket].size()-1;slot>=0;slot--){Paper old=chosen[bucket][slot];chosen[bucket].erase(chosen[bucket].begin()+slot);vector<int>bc(256);for(auto&list:chosen)for(auto pp:list)for(int v=0;v<256;v++)if(!((A[v]^pp.b)&pp.m))bc[v]=max(bc[v],quality(pp.m,pp.b,pp.bank,v));int bestGain=0,bestid=-1;for(int v=0;v<256;v++)if(!((A[v]^old.b)&old.m))bestGain+=max(0,quality(old.m,old.b,j,v)-bc[v]);for(int c=0;c<2;c++){if(chosen[bucket].empty()&&c!=co)continue;for(int id:cids[2*j+c]){auto&cc=cs[id];int g=0;for(int v:cc.rows)g+=max(0,quality(cc.m,cc.b,j,v)-bc[v]);if(g>bestGain){bestGain=g;bestid=id;}}}if(bestid<0)chosen[bucket].insert(chosen[bucket].begin()+slot,old);else{auto&cc=cs[bestid];Paper np{cc.m,cc.b,j};if(cc.col==co)chosen[bucket].insert(chosen[bucket].begin()+slot,np);else chosen[2*j+cc.col].push_back(np);changes++;}}}if(!changes)break;}


{
 vector<Paper>sel;for(auto&ls:chosen)for(auto pp:ls)sel.push_back(pp);int owner[256],topId[256][3],topQ[256][3],value=0;
 auto rebuild=[&](){value=0;for(int v=0;v<256;v++){for(int i=0;i<3;i++){topQ[v][i]=0;topId[v][i]=-1;}
  for(int k=0;k<(int)sel.size();k++)if(!((sel[k].b^A[v])&sel[k].m)){int q=quality(sel[k].m,sel[k].b,sel[k].bank,v),id=k;for(int i=0;i<3;i++)if(q>topQ[v][i]){swap(q,topQ[v][i]);swap(id,topId[v][i]);}}
  owner[v]=topId[v][0];value+=topQ[v][0];
 }};rebuild();
 for(int pass=0;pass<4;pass++){
  int changed=0;
  for(auto&c:cs){
   if(c.rows.size()<2)continue;
   for(int vi=0;vi<(int)c.rows.size();vi++){
    int oa=owner[c.rows[vi]];if(oa<0||sel[oa].bank!=c.bank||int(sel[oa].b>>c.bank&1)!=c.col)continue;
    for(int vj=0;vj<(int)c.rows.size();vj++)if(vi!=vj){
     int ob=owner[c.rows[vj]];if(ob<0||ob==oa)continue;auto oldb=sel[ob];U allowed=DM|((1ULL<<(oldb.bank+1))-1),m=allowed,b=0;bool first=true;
     for(int v=0;v<256;v++)if((owner[v]==oa||owner[v]==ob)&&((A[v]^c.b)&c.m)){
      if(first){first=false;b=A[v];}else m&=~(b^A[v]);
     }
     if(first)continue;if(!(m>>oldb.bank&1)||((b^oldb.b)>>oldb.bank&1))continue;b&=m;
     int total=0;for(int v=0;v<256;v++){
      int q=0;for(int i=0;i<3;i++)if(topId[v][i]!=oa&&topId[v][i]!=ob){q=topQ[v][i];break;}
      if(!((A[v]^c.b)&c.m))q=max(q,quality(c.m,c.b,c.bank,v));
      if(!((A[v]^b)&m))q=max(q,quality(m,b,oldb.bank,v));total+=q;
     }
     if(total>value){sel[oa]={c.m,c.b,c.bank};sel[ob]={m,b,oldb.bank};rebuild();changed++;break;}
    }
   }
  }
  if(!changed)break;
 }
 for(auto&ls:chosen)ls.clear();for(auto pp:sel)chosen[2*pp.bank+int(pp.b>>pp.bank&1)].push_back(pp);
}
vector<U>trainZ(256),trainO(256);
for(int v=0;v<256;v++){int best=-100000;U m=0;for(auto&ls:chosen)for(auto pp:ls)if(!((pp.b^A[v])&pp.m)){int q=quality(pp.m,pp.b,pp.bank,v);if(q>best){best=q;m=pp.m;}}trainZ[v]=DM&~m&~A[v];trainO[v]=DM&~m&A[v];}
vector<int>leafOrder(D);iota(leafOrder.begin(),leafOrder.end(),H);
int sign[256][64]={};for(int v=0;v<256;v++)for(int j=H;j<64;j++)sign[v][j]=((trainO[v]>>j)&1)-((trainZ[v]>>j)&1);
int walk[256][65];auto rebuild=[&](){int cost=0;for(int v=0;v<256;v++){walk[v][0]=pc(trainZ[v]);int best=walk[v][0];for(int i=0;i<D;i++){walk[v][i+1]=walk[v][i]+sign[v][leafOrder[i]];best=min(best,walk[v][i+1]);}cost+=best;}return cost;};
int current=rebuild(),bestCost=current;vector<int>bestOrder=leafOrder;mt19937_64 srng(883718);
for(int it=0;it<12000;it++){
 int a=srng()%D,b=srng()%D;if(a==b)continue;if(a>b)swap(a,b);int candidate=0;
 for(int v=0;v<256;v++){int delta=sign[v][leafOrder[b]]-sign[v][leafOrder[a]],best=100;for(int k=0;k<=D;k++)best=min(best,walk[v][k]+((a<k&&k<=b)?delta:0));candidate+=best;}
 double temp=1.5*(1.0-it/12000.0)+0.1;double randv=(srng()>>11)*0x1.0p-53;
 if(candidate<=current||randv<exp((current-candidate)/temp)){swap(leafOrder[a],leafOrder[b]);current=rebuild();if(current<bestCost){bestCost=current;bestOrder=leafOrder;}}
}
leafOrder=bestOrder;int leafRank[64]={},leafForBit[64]={};for(int i=0;i<D;i++){leafRank[leafOrder[i]]=i;leafForBit[leafOrder[i]]=i;}
vector<Paper>p;for(int j:leafOrder)p.push_back({1ULL<<j,0,-1});int bg=p.size();p.push_back({DM,DM,-1});for(int j=0;j<H;j++)for(int z=0;z<(int)max(chosen[2*j].size(),chosen[2*j+1].size());z++)for(int c=0;c<2;c++)if(z<(int)chosen[2*j+c].size())p.push_back(chosen[2*j+c][z]);while(p.size()<192)p.push_back({0,0,-1});double designtime=chrono::duration<double>(chrono::steady_clock::now()-start).count();

vector<double>freq(192,0.25);
for(int v=0;v<256;v++){
 vector<pair<int,double>>matches;double sum=0;for(int k=0;k<192;k++)if(p[k].bank>=0&&!((p[k].b^A[v])&p[k].m)){double w=exp(quality(p[k].m,p[k].b,p[k].bank,v)/64.0);matches.push_back({k,w});sum+=w;}
 for(auto[k,w]:matches)freq[k]+=w/sum;
}
double prior=argc>4?atof(argv[4]):4;if(prior>0)for(double&w:freq)w*=prior;

{
 vector<Paper>np;vector<double>nf;for(int i=0;i<=D;i++){np.push_back(p[i]);nf.push_back(freq[i]);}
 for(int j=0;j<H;j++){
  vector<int>ids;for(int k=D+1;k<192;k++)if(p[k].bank==j)ids.push_back(k);
  sort(ids.begin(),ids.end(),[&](int a,int b){return freq[a]>freq[b];});
  int other=1;while(!(((p[ids[other]].b^p[ids[0]].b)>>j)&1))other++;
  int id=ids[other];ids.erase(ids.begin()+other);ids.insert(ids.begin()+1,id);
  for(int k:ids){np.push_back(p[k]);nf.push_back(freq[k]);}
 }
 p=np;freq=nf;
}
{string out_;for(int k=0;k<192;k++){for(int j=0;j<64;j++)out_+=(p[k].m>>j&1)?char('0'+((p[k].b^(p[k].m&flip))>>j&1)):'.';out_+='\n';}cout<<out_<<flush;}
vector<int>ord(192),checkerOrd(192);iota(ord.begin(),ord.end(),0);iota(checkerOrd.begin(),checkerOrd.end(),0);auto render=[&](const vector<int>&o){U mask=0,x=0;for(int k:o){x|=p[k].b&~mask;mask|=p[k].m;}return x;};int baselineSum=0;vector<int>controlActives;vector<int>oldLeft(192,-1);int active=-1,controlActive=-1,dataActive=-1,total=0,dataops=0,fetchops=0,handleops=0,removeops=0,promoteops=0,basecount=0;vector<int>hist(385);int last=-1;for(int t=0;t<Q;t++){int a;if(!(cin>>a)||a<0)return 0;baselineSum+=last<0?pc(originalA[a]):pc(originalA[a]^originalA[last]);last=a;U target=A[a];int steps=0;vector<pair<int,int>>operations;auto act=[&](int k,int d){U cover=0;bool found=false;int i=0;for(;i<192;i++){int x=ord[i];if(x==k){assert(p[k].m&~cover);found=true;break;}cover|=p[x].m;}assert(found);ord.erase(ord.begin()+i);ord.insert(ord.begin()+d,k);steps++;operations.push_back({k,d});};

auto placeAfter=[&](int k,int anchor){int d=0,after=-1;for(int x:ord)if(x!=k){if(x==anchor)after=d+1;d++;}assert(after>=0);act(k,after);};

auto insertBank=[&](int id,const vector<int>&bank,int at){
 int anchor=at<(int)bank.size()?bank[at]:-1;
 if(anchor>=0){int d=0;for(int k:ord)if(k!=id){if(k==anchor)break;d++;}act(id,d);}
 else placeAfter(id,bank.back());
};
vector<bool>relaxHead(H,false);
auto repairHead=[&](int id,bool returning){
 int j=p[id].bank;vector<int>bank;for(int k:ord)if(k!=id&&p[k].bank==j)bank.push_back(k);
 double best=1e100;int at=-1;
 for(int d=0;d<=(int)bank.size();d++){
  vector<int>bs=bank;bs.insert(bs.begin()+d,id);
  if(!relaxHead[j]&&(((p[bs[0]].b^target)>>j)&1))continue;
  if(!(((p[bs[0]].b^p[bs[1]].b)>>j)&1))continue;
  double score=0;for(int i=0;i<(int)bs.size();i++)score+=freq[bs[i]]*i;
  if(score<best){best=score;at=d;}
 }
 assert(at>=0);insertBank(id,bank,at);
};
auto retire=[&](int id){repairHead(id,true);};
auto flipHead=[&](int id){repairHead(id,false);};



int prevMain=active;vector<int>originalSnapshot=ord;
if(active>=0){retire(active);removeops++;active=-1;}
vector<int>snapshot=ord,oldControllers;
for(int id:ord)if(find(controlActives.begin(),controlActives.end(),id)!=controlActives.end())oldControllers.push_back(id);
vector<bool>reusable(192,false);
for(int i=0;i<(int)oldControllers.size();i++){
 int id=oldControllers[i];bool good=true;
 for(int j=i+1;j<(int)oldControllers.size();j++)if(p[id].m>>p[oldControllers[j]].bank&1)good=false;
 reusable[id]=good&&id!=dataActive;
}
for(int id:oldControllers){retire(id);removeops++;}controlActives.clear();
U x=render(ord);int he=pc((x^target)&~DM);vector<U>pref(1,0);vector<int>leaves;int bcut=0;for(int k:ord){if(k==bg)bcut=leaves.size();if(k<bg){leaves.push_back(k);pref.push_back(pref.back()|p[k].m);}}

struct BP{int cost,k,t;bool keep;};auto baseplan=[&](U holes){U z=holes&~target,o=holes&target;int t=0;for(int i=0;i<D;i++)if(z&p[leaves[i]].m)t=i+1;BP best{999,bcut,t,true};if(!(z&~pref[bcut]))best.cost=pc(o&pref[bcut]);int c=max(bcut,t);for(int k=0;k<=t;k++){int zm=pc(z&~pref[k]),om=pc(o&pref[k]);int fc=k+zm;int fm=(fc!=c),helper=0;if(c==D&&fm&&om==0){helper=1;if(fc==D-1)fm=0;}int cost=(bcut<t)+zm+om+fm+helper;int finalcut=k+zm-om;int bestcut=best.keep?bcut-pc(o&pref[bcut]):best.k+pc(z&~pref[best.k])-pc(o&pref[best.k]);if(cost<best.cost||(cost==best.cost&&finalcut>bestcut))best={cost,k,t,false};}return best;};


U holes=DM;BP bp=baseplan(holes);double best=bp.cost+he;int bid=-1,retained=-1,retained2=-1,chosenData=-1;vector<pair<int,int>> controllers;int rank[64]={};vector<int>rr(192);for(int k:ord)if(p[k].bank>=0)rr[k]=rank[p[k].bank]++;
vector<int>oldActive=oldControllers;if(prevMain>=0)oldActive.push_back(prevMain);auto rawRank=rr;
for(int id:ord)if(p[id].bank>=0)for(int old:oldActive)if(old!=id&&p[old].bank==p[id].bank&&rawRank[old]<rawRank[id])rr[id]--;
auto assess=[&](int main,int special){
 U mm=main<0?0:p[main].m,hs=DM&~mm;U usedBanks=main<0?0ULL:1ULL<<p[main].bank;vector<pair<int,int>>initialPicks;
 if(special>=0){bool all=!((p[special].b^target)&p[special].m&hs);hs&=~(all?p[special].m:(p[special].m&~p[special].b));mm|=p[special].m&~DM;usedBanks|=1ULL<<p[special].bank;initialPicks.push_back({special,0});}
 U errors=(x^target)&~DM&~mm;auto plan=baseplan(hs);double fixed=plan.cost+(main<0?0:rr[main]+1.7)+(special<0?0:rr[special]+1.7);
 struct State{U mask,banks;int left,cost,reuse,reuse2;vector<pair<int,int>>picks;};
 vector<State>beam{{mm&~DM,usedBanks,0,0,-1,-1,initialPicks}};
 int bestCost=10*pc(errors),bestReuse=-1,bestReuse2=-1;vector<pair<int,int>>bestSel=initialPicks;
 for(int depth=0;depth<4-(special>=0);depth++){
  vector<pair<double,State>>next;

  for(auto&st:beam)for(int id:ord)if(p[id].bank>=0&&!(st.banks>>p[id].bank&1)){
   bool blockedByReuse=false;for(int r:{st.reuse,st.reuse2})if(r>=0){int left=-1;for(auto[k,l]:st.picks)if(k==r)left=l;if(p[id].bank>=left&&(p[r].m>>p[id].bank&1))blockedByReuse=true;}if(blockedByReuse)continue;
   U cm=p[id].m&~DM;U wrong=(p[id].b^target)&cm&~st.mask;
   int minLeft=max(st.left,wrong?64-__builtin_clzll(wrong):0);
   for(int keep=0;keep<4;keep++){
    int l=minLeft,co=10*rr[id]+17,reuse=st.reuse,reuse2=st.reuse2;
    if(keep){
     if(st.reuse2>=0)continue;
     if(st.reuse>=0&&((p[id].m>>p[st.reuse].bank&1)||(p[st.reuse].m>>p[id].bank&1)))continue;
     if(keep==3){if(id!=prevMain)continue;}else if(!reusable[id])continue;
     l=keep==1?oldLeft[id]:minLeft;if(l<minLeft)continue;if(st.reuse>=0){int rl=-1;for(auto[k,ll]:st.picks)if(k==st.reuse)rl=ll;if(rl==l)continue;}
     if(keep==3){bool safe=true;for(int k:oldControllers)if(oldLeft[k]>l&&(p[id].m>>p[k].bank&1))safe=false;if(!safe)continue;}
     bool blocked=false;U banks=st.banks;while(banks){int j=__builtin_ctzll(banks);banks&=banks-1;if(j>=l&&(p[id].m>>j&1))blocked=true;}if(blocked)continue;
     co=keep==1?-3:7;if(reuse<0)reuse=id;else reuse2=id;
    }
    if(l>p[id].bank)continue;
    U effect=cm&(~0ULL<<l),newMask=st.mask|effect;if(newMask==st.mask&&!keep)continue;
    State ns{newMask,st.banks|(1ULL<<p[id].bank),l,st.cost+co,reuse,reuse2,st.picks};
    ns.picks.push_back({id,l});int score=ns.cost+10*pc(errors&~ns.mask);
    if(score<bestCost){bestCost=score;bestSel=ns.picks;bestReuse=ns.reuse;bestReuse2=ns.reuse2;}
    if(ns.cost>=bestCost+10)continue;
    double priority=score-0.05*pc(newMask);next.push_back({priority,move(ns)});
   }
  }
  sort(next.begin(),next.end(),[](auto&a,auto&b){return a.first<b.first;});
  beam.clear();for(auto&[score,ns]:next){bool dup=false;for(auto&st:beam)if(st.mask==ns.mask&&st.banks==ns.banks&&st.left==ns.left&&st.reuse==ns.reuse&&st.reuse2==ns.reuse2){dup=true;break;}if(!dup)beam.push_back(move(ns));if(beam.size()>=16)break;}
  if(beam.empty())break;
 }
 double cost=fixed+bestCost/10.0;
 if(cost<best){best=cost;bid=main;bp=plan;holes=hs;controllers=bestSel;retained=bestReuse;retained2=bestReuse2;chosenData=special;}
};

vector<int>mains{-1};for(int k:ord)if(p[k].bank>=0&&!((p[k].b^target)&p[k].m))mains.push_back(k);
for(int main:mains)assess(main,-1);
for(int main:mains){
 U mm=main<0?0:p[main].m,hh=DM&~mm;auto oldplan=baseplan(hh);vector<pair<double,int>>specials;
 for(int id:ord)if(p[id].bank>=0&&(main<0||p[id].bank!=p[main].bank)){
  if((p[id].b^target)&p[id].m&~DM&~mm)continue;U zeros=p[id].m&~p[id].b;
  if(zeros&hh&target)continue;bool all=!((p[id].b^target)&p[id].m&hh);auto plan=baseplan(hh&~(all?p[id].m:zeros));if(plan.cost>=oldplan.cost)continue;
  int fixed=pc((x^target)&~DM&~mm&p[id].m);
  if(oldplan.cost-plan.cost+fixed<rr[id]+1)continue;
  double cost=plan.cost+rr[id]+1.7+pc((x^target)&~DM&~(mm|p[id].m));specials.push_back({cost,id});
 }
 sort(specials.begin(),specials.end());for(int i=0;i<(int)min<size_t>(2,specials.size());i++)assess(main,specials[i].second);
}

if(bid<0)basecount++;


int dataChoice=chosenData;
if(dataChoice<0&&!controllers.empty()&&controllers[0].second==0){
 int id=controllers[0].first;if(id!=retained&&id!=retained2){
  U zeros=p[id].m&~p[id].b;if(!(zeros&holes&target)){
   bool all=!((p[id].b^target)&p[id].m&holes);U newHoles=holes&~(all?p[id].m:zeros);auto plan=baseplan(newHoles);if(plan.cost<bp.cost){bp=plan;holes=newHoles;dataChoice=id;}
  }
 }
}
bool dataAll=dataChoice>=0&&!((p[dataChoice].b^target)&p[dataChoice].m&DM&~(bid<0?0ULL:p[bid].m));
dataActive=dataChoice;

{
 U finalMask=bid>=0?p[bid].m:0;for(auto[id,l]:controllers)finalMask|=p[id].m&(~0ULL<<l);for(int j=0;j<H;j++)relaxHead[j]=(finalMask>>j)&1;
 vector<int>newByBank(H,-1);if(bid>=0)newByBank[p[bid].bank]=bid;for(auto[id,l]:controllers)newByBank[p[id].bank]=id;
 vector<int>keepers;if(retained>=0)keepers.push_back(retained);if(retained2>=0)keepers.push_back(retained2);
 auto isKept=[&](int id){return id>=0&&(id==retained||id==retained2);};
 auto newLeftOf=[&](int id){for(auto[k,l]:controllers)if(k==id)return l;return -1;};
 ord=originalSnapshot;operations.clear();steps=0;removeops-=oldControllers.size()+(prevMain>=0);controlActives.clear();
 auto returnOld=[&](int id){int goal=newByBank[p[id].bank];if(goal>=0&&goal!=id)placeAfter(id,goal);else retire(id);removeops++;};
 if(isKept(prevMain)){
  int left=newLeftOf(prevMain),d=0;for(int k:ord)if(k!=prevMain){if(p[k].bank==left&&find(oldControllers.begin(),oldControllers.end(),k)==oldControllers.end())break;d++;}act(prevMain,d);removeops++;
 }else if(prevMain>=0)returnOld(prevMain);
 for(int id:oldControllers)if(!isKept(id))returnOld(id);
 controlActives=keepers;
 for(int id:keepers)if(id!=prevMain){
  int left=newLeftOf(id);if(left==oldLeft[id])continue;
  int pi=-1;for(int i=0;i<(int)controllers.size();i++)if(controllers[i].first==id)pi=i;
  int d=0;for(int k:ord)if(k!=id){
   bool later=false;for(int i=pi+1;i<(int)controllers.size();i++)if(controllers[i].second==left&&controllers[i].first==k)later=true;
   if(later||(p[k].bank==left&&!isKept(k)))break;d++;
  }act(id,d);promoteops++;
 }
}
for(auto[id,l]:controllers)oldLeft[id]=l;



auto runData=[&](BP bp,U holes){
auto insertionValues=[&](int id){
 vector<int>bits;for(int k:ord)if(k<bg&&k!=id)bits.push_back(__builtin_ctzll(p[k].m));int m=bits.size(),bit=__builtin_ctzll(p[id].m);vector<int>value(m+1);
 for(int v=0;v<256;v++){
  int walk[65],pre[65],suf[65];walk[0]=pc(trainZ[v]);pre[0]=walk[0];
  for(int i=0;i<m;i++){walk[i+1]=walk[i]+sign[v][bits[i]];pre[i+1]=min(pre[i],walk[i+1]);}
  suf[m]=walk[m];for(int i=m-1;i>=0;i--)suf[i]=min(suf[i+1],walk[i]);
  for(int i=0;i<=m;i++)value[i]+=min(pre[i],suf[i]+sign[v][bit]);
 }
 return value;
};
int beforedata=dataops;U o=holes&target,z=holes&~target;
if(!bp.keep){if(bcut<bp.t){act(bg,bp.t);dataops++;}U movez=z&~pref[bp.k];int fc=bp.k+pc(movez);while(movez){int j=__builtin_ctzll(movez);movez&=movez-1;
int id=leafForBit[j],lim=bp.k+pc(z&~pref[bp.k])-pc(movez)-1;
auto potential=insertionValues(id);int bestAt=0,bestInv=100000000;vector<int>ls;for(int k:ord)if(k!=id&&k<bg)ls.push_back(k);
for(int at=0;at<=lim;at++){int inv=0;for(int i=0;i<(int)ls.size();i++)inv+=(i<at)?(leafRank[__builtin_ctzll(p[ls[i]].m)]>leafRank[j]):(leafRank[__builtin_ctzll(p[ls[i]].m)]<leafRank[j]);inv+=100*potential[at];if(inv<bestInv){bestInv=inv;bestAt=at;}}
act(id,bestAt);dataops++;}
int posbg=find(ord.begin(),ord.end(),bg)-ord.begin();if(posbg==D&&fc<D){U opts=o&pref[bp.k];if(!opts)opts=DM&~pref[bp.k]&~z;assert(opts);int j=__builtin_ctzll(opts),helper=leafForBit[j];int orig=find(leaves.begin(),leaves.end(),helper)-leaves.begin();act(helper,D);dataops++;if(orig<bp.k)fc--;}
posbg=find(ord.begin(),ord.end(),bg)-ord.begin();if(posbg!=fc){act(bg,fc);dataops++;}}
while(true){int bad=-1;for(int k:ord){if(k==bg)break;if(k<bg&&(p[k].m&o)){bad=k;break;}}if(bad<0)break;
auto potential=insertionValues(bad);int bestAt=D,bestInv=100000000;vector<int>ls;for(int k:ord)if(k!=bad&&k<=bg)ls.push_back(k);int pos=find(ls.begin(),ls.end(),bg)-ls.begin();
int desired=leafRank[__builtin_ctzll(p[bad].m)];for(int at=pos+1;at<=D;at++){int inv=0;for(int i=0;i<(int)ls.size();i++)if(ls[i]!=bg){int r=leafRank[__builtin_ctzll(p[ls[i]].m)];inv+=i<at?r>desired:r<desired;}inv+=100*potential[at-1];if(inv<bestInv){bestInv=inv;bestAt=at;}}
act(bad,bestAt);dataops++;}assert(dataops-beforedata==bp.cost);



};
int dataCut=dataAll?0:-1;
if(dataChoice>=0&&!dataAll){
 U mainHoles=DM&~(bid<0?0ULL:p[bid].m),newHoles=mainHoles&~p[dataChoice].m;auto candidate=baseplan(newHoles);
 if(candidate.cost<bp.cost){
  auto savedOrder=ord;auto savedOps=operations;int savedSteps=steps,savedData=dataops;
  runData(candidate,newHoles);
  int lower=0,upper=find(ord.begin(),ord.end(),bg)-ord.begin();
  for(int at=0;at<192;at++){int k=ord[at];if(k<bg&&(p[k].m&mainHoles&p[dataChoice].m&p[dataChoice].b)){
   if(p[k].m&target)upper=min(upper,at);else lower=max(lower,at+1);
  }}
  if(lower<=upper){bp=candidate;holes=newHoles;dataCut=lower;}
  ord=savedOrder;operations=savedOps;steps=savedSteps;dataops=savedData;
 }
}
runData(bp,holes);

vector<int>picks;if(bid>=0)picks.push_back(bid);for(auto[id,l]:controllers)if(id!=retained&&id!=retained2)picks.push_back(id);sort(picks.begin(),picks.end(),[&](int a,int b){return p[a].bank<p[b].bank;});for(int id:picks){
int j=p[id].bank;vector<int>prefix,tail;bool reached=false;
for(int k:ord)if(p[k].bank==j){if(k==id){reached=true;continue;}(reached?tail:prefix).push_back(k);}
vector<int>bestOrder;double bestScore=1e100;
vector<int>firsts=prefix;if(!tail.empty())firsts.push_back(tail[0]);
for(int first:firsts)if(((p[first].b^p[id].b)>>j)&1){
 vector<int>pp,tt;for(int k:prefix)if(k!=first)pp.push_back(k);for(int k:tail)if(k!=first)tt.push_back(k);
 sort(pp.begin(),pp.end(),[&](int a,int b){return freq[a]>freq[b];});int np=pp.size(),nt=tt.size();
 double dp[17][17];bool takeP[17][17];for(int x=0;x<=np;x++)for(int y=0;y<=nt;y++)dp[x][y]=1e100;dp[0][0]=0;
 for(int x=0;x<=np;x++)for(int y=0;y<=nt;y++){
  int at=1+x+y;
  if(x<np&&dp[x+1][y]>dp[x][y]+at*freq[pp[x]]){dp[x+1][y]=dp[x][y]+at*freq[pp[x]];takeP[x+1][y]=true;}
  if(y<nt&&dp[x][y+1]>dp[x][y]+at*freq[tt[y]]){dp[x][y+1]=dp[x][y]+at*freq[tt[y]];takeP[x][y+1]=false;}
 }
 if(dp[np][nt]<bestScore){bestScore=dp[np][nt];vector<int>rev;int x=np,y=nt;while(x||y){if(takeP[x][y])rev.push_back(pp[--x]);else rev.push_back(tt[--y]);}reverse(rev.begin(),rev.end());bestOrder={first};bestOrder.insert(bestOrder.end(),rev.begin(),rev.end());}
}
assert(!bestOrder.empty());
for(int head:prefix){
 vector<int>below;bool after=false;for(int k:ord)if(p[k].bank==j){if(k==id)after=true;else if(after)below.push_back(k);}
 int position=find(bestOrder.begin(),bestOrder.end(),head)-bestOrder.begin(),anchor=-1;
 for(int z=position+1;z<(int)bestOrder.size();z++)if(find(below.begin(),below.end(),bestOrder[z])!=below.end()){anchor=bestOrder[z];break;}
 if(anchor>=0){int d=0;for(int k:ord)if(k!=head){if(k==anchor)break;d++;}act(head,d);}else placeAfter(head,below.empty()?id:below.back());
 fetchops++;
}
if(id==bid){act(id,0);active=id;}else{
 int l=-1,pi=-1;for(int i=0;i<(int)controllers.size();i++)if(controllers[i].first==id){l=controllers[i].second;pi=i;}assert(l>=0);
 int d=-1,idx=0;for(int k:ord){if(k==id)continue;
 bool isLater=false;for(int i=pi+1;i<(int)controllers.size();i++)if(controllers[i].second==l&&controllers[i].first==k)isLater=true;
 if(isLater||(p[k].bank==l&&k!=active&&find(controlActives.begin(),controlActives.end(),k)==controlActives.end())){d=idx;break;}idx++;}
 assert(d>=0);if(id==dataChoice){if(dataCut>=0)d=dataCut+(active>=0);else{d=0;for(int k:ord)if(k!=id){if(k==bg)break;d++;}}}act(id,d);controlActives.push_back(id);
}promoteops++;}
for(int j=0;j<H;j++)if((render(ord)^target)>>j&1){int owner=-1;for(int k:ord)if(p[k].m>>j&1){owner=k;break;}assert(p[owner].bank==j);flipHead(owner);handleops++;}

if(prior>0){if(active>=0)freq[active]++;for(int k:controlActives)freq[k]++;}
assert((int)operations.size()==steps);
for(auto[k,d]:operations){
 assert(0<=k&&k<192&&0<=d&&d<192);int at=-1;U covered=0;
 for(int i=0;i<192;i++){if(checkerOrd[i]==k){assert(p[k].m&~covered);at=i;break;}covered|=p[checkerOrd[i]].m;}
 assert(at>=0);checkerOrd.erase(checkerOrd.begin()+at);checkerOrd.insert(checkerOrd.begin()+d,k);
}
assert(checkerOrd==ord);
assert(render(ord)==target);U realMask=0,realX=0;for(int k:ord){realX|=(p[k].b^(p[k].m&flip))&~realMask;realMask|=p[k].m;}assert(realMask==~0ULL);assert(realX==originalA[a]);assert(steps<=384);total+=steps;hist[steps]++;assert((int)operations.size()==steps);{string out_=to_string(operations.size())+"\n";for(auto[k_,d_]:operations)out_+=to_string(k_)+" "+to_string(d_)+"\n";cout<<out_<<flush;}}
int mx=0;for(int i=0;i<385;i++)if(hist[i])mx=i;cerr<<"H "<<H<<" seed "<<seed<<" candidates "<<cs.size()<<" bestcov "<<double(ng)/256<<" avg "<<double(total)/Q<<" design_s "<<designtime<<" total_s "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<" components "<<double(dataops)/Q<<","<<double(fetchops)/Q<<","<<double(handleops)/Q<<","<<double(removeops)/Q<<","<<double(promoteops)/Q<<" baseline_avg "<<double(baselineSum)/Q<<" unused_template "<<basecount<<" max "<<mx<<endl;}
