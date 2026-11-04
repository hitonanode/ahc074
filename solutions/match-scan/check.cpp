#define VERIFY_SINGLE_SCAN
#define MATCH_SCAN_RESEARCH
#include "common.hpp"
int main(int argc,char**argv) {
 if(argc<3)return 2;auto s=head::load(argv[1],argv[2]);if(!s)return 3;
 auto original=recover(*s);original->refresh_reset();
 for(int mode=0;mode<2;mode++) {
  auto d=*original;match_scan_mode=mode;
  // The slow mode is only a reference; its unset donor entries are evaluated
  // lazily, so the full table assertions apply to the scanning mode.
  if(!mode)continue;
  auto stats=rematch_probability(d,4,1,2,true,true);
  std::cout<<stats.iterations<<' '<<stats.changed<<' '<<stats.decrease<<' '<<stats.seconds<<'\n';
 }
}
