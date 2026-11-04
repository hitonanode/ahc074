#include "exact.hpp"
#include <sstream>
int main(int argc,char**argv){
 if(argc<3)return 2;std::ifstream in(argv[1]);int K,P,N;in>>K>>P>>N;if(K>9||N!=3||P!=256)return 3;
 int limit=argc>3?std::stoi(argv[3]):3000;Model model;model.build(N,K);Design original;original.op.resize(K);original.bk.resize(K);
 std::vector<int>color(K),allowed(K);for(int k=0;k<K;k++){int id,col;in>>id>>col>>original.op[k]>>color[k]>>allowed[k];original.bk[k]=color[k]&original.op[k];}
 std::map<std::tuple<int,int,int>,int>counts;for(int u=0;u<P;u++){int k,m,c;in>>k>>m>>c;if(k>=0)counts[{k,7,c}]++;else if(m)counts[{k,m,c&m}]++;}
 Exact e(model);for(auto[key,n]:counts){auto[k,m,c]=key;e.events.push_back({k,m,c,n});}
 Design d=original;std::stringstream stream(argv[2]);std::string cell;int k=0;while(std::getline(stream,cell,',')){if(k>=K)return 4;d.op[k]=std::stoi(cell);if(d.op[k]&~allowed[k])return 5;d.bk[k]=d.op[k]&color[k];k++;}if(k!=K)return 6;
 auto start=std::chrono::steady_clock::now();std::cout<<std::setprecision(12)<<"[";
 int i=0;for(auto current:{original,d}){e.prepare_actual(current);std::fill(e.h.begin(),e.h.end(),0);double value=e.solve_actual(limit,2e-6);std::cout<<(i++?",":"")<<"{\"value\":"<<value<<",\"lower\":"<<e.g_lo<<",\"upper\":"<<e.g_hi<<",\"iterations\":"<<e.iterations<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}"<<std::flush;}std::cout<<"]\n";
}
