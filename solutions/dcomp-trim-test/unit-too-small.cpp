#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
#define STR1(x) #x
#define STR(x) STR1(x)
#define SUM(x) ((x) + \
	2)
#define BLOCK 1   + 2
#define UNUSED_BACKSLASH \/**/ 
#if 0 && __COUNTER__ >= 0
not compiled
#endif
constexpr int counter=__COUNTER__;
constexpr char q[]="a\
    b//c";
constexpr char8_t raw[]=u8R"tag(a
    // text /* not a comment */
    #if LOCAL_BENCH
    \
  tail)tag";
constexpr auto fake=R"tag(abc )ta\
g" body
    spaces)tag";
static_assert(fake[7]=='\\' && fake[8]=='\n' && fake[10]=='"');
constexpr char c='\'';
constexpr auto n=12'345;
constexpr char ss[]=STR(alpha beta);
static_assert(SUM(3)==5 && BLOCK==3);
static_assert(q[1]==' ' && q[5]=='b');
static_assert(raw[2]==' ' && raw[3]==' ' && raw[6]=='/');
static_assert(n==12345 && ss[5]==' ');


#if defined(FLAG)
constexpr int v=11;
#else
constexpr int v=12;
#endif
#if defined(FLAG)



constexpr int w=21;

#else
constexpr int w=22;


#endif



static_assert(CLOCK_SCALE > 0);
int main(){return v+w+counter;}
