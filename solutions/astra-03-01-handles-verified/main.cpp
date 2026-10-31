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
using namespace std;using U=uint64_t;int pc(U x){return __builtin_popcountll(x);}struct Paper{U m,b;int bank=-1;};struct Cand{U m,b;vector<int> rows;int w;};struct Entry{int gain,id,bank,color,version;bool operator<(const Entry&o)const{return gain<o.gain;}};
int main(int argc,char**argv){int H=argc>1?atoi(argv[1]):16,seed=argc>2?atoi(argv[2]):1,Q=argc>3?atoi(argv[3]):1024;mt19937_64 rng(seed);U DM=~((1ULL<<H)-1);int D=64-H,M=(192-D-1)/2*2;int N_,K_,P_,R_;cin>>N_>>K_>>P_>>R_;vector<U>A(256);for(U &x:A){string s_;cin>>s_;x=0;for(int j=0;j<64;j++)if(s_[j]=='1')x|=1ULL<<j;}vector<U>originalA=A;assert(set<U>(A.begin(),A.end()).size()==256);U flip=0;for(int j=H;j<64;j++){int ones=0;for(U x:A)ones+=(x>>j)&1;if(ones>128)flip|=1ULL<<j;}for(U&x:A)x^=flip;auto start=chrono::steady_clock::now();vector<Cand> cs;set<pair<U,U>> seen;auto add=[&](U m,U b){b&=m;if(pc(m)<5||!seen.insert({m,b}).second)return;Cand c{m,b,{},pc(b)};for(int p=0;p<256;p++)if(!((A[p]^b)&m))c.rows.push_back(p);cs.push_back(move(c));};for(U a:A)add(DM,a);for(int p=0;p<256;p++)for(int q=0;q<p;q++)add(DM&~(A[p]^A[q]),A[p]);
for(int p=0;p<256;p++){vector<pair<int,int>> near;for(int q=0;q<256;q++)if(p!=q)near.push_back({pc((A[p]^A[q])&DM),q});sort(near.begin(),near.end());for(int tr=0;tr<24;tr++){int q=near[rng()%32].second;U m=DM&~(A[p]^A[q]);vector<int>used{p,q};for(int depth=0;depth<5;depth++){add(m,A[p]);vector<pair<int,int>> opts;for(int r=0;r<256;r++)if(find(used.begin(),used.end(),r)==used.end())opts.push_back({pc(m&~(A[p]^A[r])),r});partial_sort(opts.begin(),opts.begin()+4,opts.end(),greater<pair<int,int>>());int r=opts[rng()%3].second;m&=~(A[p]^A[r]);used.push_back(r);}}}
vector<array<int,2>> cap(H);for(int j=0;j<H;j++)cap[j]={M/(2*H)+(j<(M/2)%H),M/(2*H)+(j<(M/2)%H)};vector<int>covered(256);int ver=0;auto evaluate=[&](int id){auto&c=cs[id];int g[64][2]={};for(int p:c.rows){int v=max(0,c.w-covered[p]);if(v)for(int j=0;j<H;j++)g[j][A[p]>>j&1]+=v;}Entry e{0,id,0,0,ver};for(int j=0;j<H;j++)for(int b=0;b<2;b++)if(cap[j][b]>0&&g[j][b]>e.gain)e={g[j][b],id,j,b,ver};return e;};priority_queue<Entry> heap;for(int i=0;i<(int)cs.size();i++)heap.push(evaluate(i));vector<vector<Paper>> chosen(H*2);int ng=0;for(int t=0;t<M;t++){Entry e;while(true){e=heap.top();heap.pop();if(e.version==ver)break;heap.push(evaluate(e.id));}auto&c=cs[e.id];cap[e.bank][e.color]--;for(int p:c.rows)if((int)(A[p]>>e.bank&1)==e.color)covered[p]=max(covered[p],c.w);chosen[2*e.bank+e.color].push_back({c.m|(1ULL<<e.bank),c.b|(U(e.color)<<e.bank),e.bank});ver++;heap.push(evaluate(e.id));ng+=e.gain;}

int changes=0;for(int outer=0;outer<3;outer++){
for(int pass=0;pass<3;pass++){int done=0;for(int bucket=0;bucket<2*H;bucket++)for(int slot=0;slot<(int)chosen[bucket].size();slot++){
int bank=bucket/2,color=bucket%2;vector<int>bc(256);for(int bb=0;bb<2*H;bb++)for(int ss=0;ss<(int)chosen[bb].size();ss++){if(bb==bucket&&ss==slot)continue;auto pp=chosen[bb][ss];int w=pc(pp.b&DM);for(int v=0;v<256;v++)if(!((A[v]^pp.b)&pp.m))bc[v]=max(bc[v],w);}
auto old=chosen[bucket][slot];int oldw=pc(old.b&DM),bestg=0,bestid=-1;for(int v=0;v<256;v++)if(!((A[v]^old.b)&old.m))bestg+=max(0,oldw-bc[v]);for(int id=0;id<(int)cs.size();id++){auto&cc=cs[id];int gain=0;for(int v:cc.rows)if((int)(A[v]>>bank&1)==color)gain+=max(0,cc.w-bc[v]);if(gain>bestg){bestg=gain;bestid=id;}}
if(bestid>=0){auto&cc=cs[bestid];chosen[bucket][slot]={cc.m|(1ULL<<bank),cc.b|(U(color)<<bank),bank};done++;changes++;}}
if(!done)break;}

if(outer==2)break;
int count0[64]={},count1[64]={};for(int v=0;v<256;v++){int val=-1,bits=-1;U mask=0;for(auto&bucket:chosen)for(auto pp:bucket)if(!((A[v]^pp.b)&pp.m)){int w=pc(pp.b&DM),b=pc(pp.m&DM);if(w>val||(w==val&&b>bits)){val=w;bits=b;mask=pp.m&DM;}}U holes=DM&~mask;for(int j=H;j<64;j++)if(holes>>j&1){if(A[v]>>j&1)count1[j]++;else count0[j]++;}}
U delta=0;for(int j=H;j<64;j++)if(count1[j]>count0[j])delta|=1ULL<<j;if(!delta)break;flip^=delta;for(U &x:A)x^=delta;for(auto&cc:cs){cc.b^=delta&cc.m;cc.w=pc(cc.b);}for(auto&bucket:chosen)for(auto&pp:bucket)pp.b^=delta&pp.m;
}

vector<Paper>p;for(int j=H;j<64;j++)p.push_back({1ULL<<j,0,-1});int bg=p.size();p.push_back({DM,DM,-1});for(int j=0;j<H;j++)for(int z=0;z<(int)chosen[2*j].size();z++)for(int c=0;c<2;c++)p.push_back(chosen[2*j+c][z]);while(p.size()<192)p.push_back({0,0,-1});double designtime=chrono::duration<double>(chrono::steady_clock::now()-start).count();
{string out_;for(int k=0;k<192;k++){for(int j=0;j<64;j++)out_+=(p[k].m>>j&1)?char('0'+((p[k].b^(p[k].m&flip))>>j&1)):'.';out_+='\n';}cout<<out_<<flush;}
vector<int>ord(192);iota(ord.begin(),ord.end(),0);auto render=[&](const vector<int>&o){U mask=0,x=0;for(int k:o){x|=p[k].b&~mask;mask|=p[k].m;}return x;};int baselineSum=0;int active=-1,total=0,dataops=0,fetchops=0,handleops=0,removeops=0,promoteops=0,basecount=0;vector<int>hist(100);int last=-1;for(int t=0;t<Q;t++){int a;if(!(cin>>a)||a<0)return 0;baselineSum+=last<0?pc(originalA[a]):pc(originalA[a]^originalA[last]);last=a;U target=A[a];int steps=0;vector<pair<int,int>>operations;auto act=[&](int k,int d){U cover=0;bool found=false;int i=0;for(;i<192;i++){int x=ord[i];if(x==k){assert(p[k].m&~cover);found=true;break;}cover|=p[x].m;}assert(found);ord.erase(ord.begin()+i);ord.insert(ord.begin()+d,k);steps++;operations.push_back({k,d});};
if(active>=0){act(active,191);removeops++;active=-1;}
U x=render(ord);int he=pc((x^target)&~DM);vector<U>pref(1,0);vector<int>leaves;int bcut=0;for(int k:ord){if(k==bg)bcut=leaves.size();if(k<bg){leaves.push_back(k);pref.push_back(pref.back()|p[k].m);}}
struct BP{int cost,cut;};auto baseplan=[&](U holes){U z=holes&~target,o=holes&target;int cut=0;for(int i=0;i<D;i++)if(z&p[leaves[i]].m)cut=i+1;BP best{999,bcut};if(!(z&~pref[bcut]))best={pc(o&pref[bcut]),bcut};int co=pc(o&pref[cut]);int helper=(bcut==D&&cut<D&&co==0);int cost=co+(cut!=bcut)+helper;if(cost<best.cost)best={cost,cut};return best;};
U holes=DM;BP bp=baseplan(holes);int best=bp.cost+he,bid=-1;int rank[64]={};for(int k:ord)if(p[k].bank>=0){int j=p[k].bank,r=rank[j]++;if((p[k].b^target)&p[k].m)continue;U hs=DM&~p[k].m;auto plan=baseplan(hs);int cost=plan.cost+r+1+he-((x^target)>>j&1);if(cost<best){best=cost;bid=k;bp=plan;holes=hs;}}
if(bid<0)basecount++;
int cut=bp.cut;U o=holes&target;if(cut!=bcut){if(bcut==D){U opts=o&pref[cut];if(!opts)opts=o;assert(opts);int j=__builtin_ctzll(opts),helper=j-H;int ix=find(leaves.begin(),leaves.end(),helper)-leaves.begin();act(helper,D);dataops++;if(ix<cut)cut--;}
act(bg,cut);dataops++;}
while(true){int bad=-1;for(int k:ord){if(k==bg)break;if(k<bg&&(p[k].m&o)){bad=k;break;}}if(bad<0)break;act(bad,D);dataops++;}
if(bid>=0){int j=p[bid].bank;while(true){int head=-1;for(int k:ord)if(p[k].bank==j){head=k;break;}if(head==bid)break;act(head,191);fetchops++;}act(bid,0);promoteops++;active=bid;}for(int j=0;j<H;j++)if((render(ord)^target)>>j&1){int owner=-1;for(int k:ord)if(p[k].m>>j&1){owner=k;break;}act(owner,191);handleops++;}
assert(render(ord)==target);U realMask=0,realX=0;for(int k:ord){realX|=(p[k].b^(p[k].m&flip))&~realMask;realMask|=p[k].m;}assert(realMask==~0ULL);assert(realX==originalA[a]);assert(steps<=384);total+=steps;hist[steps]++;assert((int)operations.size()==steps);{string out_=to_string(operations.size())+"\n";for(auto[k_,d_]:operations)out_+=to_string(k_)+" "+to_string(d_)+"\n";cout<<out_<<flush;}}
int mx=0;for(int i=0;i<100;i++)if(hist[i])mx=i;cerr<<"H "<<H<<" seed "<<seed<<" candidates "<<cs.size()<<" bestcov "<<double(ng)/256<<" avg "<<double(total)/Q<<" design_s "<<designtime<<" total_s "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<" components "<<double(dataops)/Q<<","<<double(fetchops)/Q<<","<<double(handleops)/Q<<","<<double(removeops)/Q<<","<<double(promoteops)/Q<<" baseline_avg "<<double(baselineSum)/Q<<" unused_template "<<basecount<<" max "<<mx<<endl;}
