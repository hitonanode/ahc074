#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>
using U=std::uint64_t;
int main(){std::mt19937_64 r(719331); std::vector<U>a(256); for(U &x:a){std::vector<int>v(64);std::iota(v.begin(),v.end(),0);std::shuffle(v.begin(),v.end(),r);for(int i=0;i<32;i++)x|=U(1)<<v[i];}for(int M:{6,7,8,9,10,12,16})for(int G:{28,32,36,40,44}){std::vector<std::pair<int,int>>es;for(int i=0;i<M;i++)for(int j=i+1;j<M;j++)es.push_back({i,j});std::shuffle(es.begin(),es.end(),r);std::array<unsigned,64>L{},R{};for(int j=0;j<G;j++){auto[x,y]=es[j%es.size()];if(r()&1)std::swap(x,y);L[j]=x;R[j]=y;}auto ok=[&](U x,U holes){unsigned adj[16]={};while(holes){int j=std::countr_zero(holes);holes&=holes-1;int x1=L[j],y=R[j];if(!(x>>j&1))std::swap(x1,y);adj[x1]|=1u<<y;}for(int k=0;k<M;k++)for(int i=0;i<M;i++)if(adj[i]>>k&1)adj[i]|=adj[k];for(int i=0;i<M;i++)if(adj[i]>>i&1)return false;return true;};U mask=(U(1)<<G)-1;int p=0,t=0,hit[256]={};for(int z=0;z<100000;z++){int u=r()%256,v=r()%256,w=r()%256;while(v==u)v=r()%256;while(w==u||w==v)w=r()%256;U d=(a[u]^a[v])&mask;if(ok(a[u],d))p++;d|=(a[u]^a[w])&mask;if(ok(a[u],d)&&ok(a[v],d)&&ok(a[w],d)){t++;hit[u]++;hit[v]++;hit[w]++;}}int covered=0;for(int z:hit)covered+=z>0;std::cout<<M<<" "<<G<<" pair="<<p/1000.0<<"% triple="<<t/1000.0<<"% covered="<<covered<<"\n";}}
