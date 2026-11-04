#define MATCH_SCAN_RESEARCH
#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto original=recover(*base);original->refresh_reset();
 std::vector<Design::Unit> reference;double ref=0;
 std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<5;mode++){
  auto d=*original;match_scan_mode=mode;auto r=rematch_probability(d,4,1,2,true,true);
  if(!mode){reference=d.unit;ref=d.cur;}
  int changed=0;for(int x=0;x<d.U;x++)changed+=d.unit[x].a!=reference[x].a||d.unit[x].b!=reference[x].b||d.unit[x].c!=reference[x].c;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"value\":"<<d.cur/P<<",\"difference\":"<<(d.cur-ref)/P<<",\"changed\":"<<changed<<",\"cycles\":"<<r.accepted_cycles<<",\"seconds\":"<<r.seconds<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
