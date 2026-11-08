"""Task14 verification. Run under flock + nice. Never execute solver binaries."""
from pathlib import Path
import sys,os,json,hashlib,subprocess,importlib.util,re,difflib
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parents[1];TMP=Path('/tmp/ahc074-trim14');TMP.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('trim_tool',R/'solutions/dcomp-notes/trim_tool.py');T=importlib.util.module_from_spec(spec);sys.modules[spec.name]=T;spec.loader.exec_module(T)
FIXTURE=r'''#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
#define STR1(x) #x
#define STR(x) STR1(x)
#define SUM(x) ((x) + \
    2)
#define BLOCK 1 /* multiline
comment inside directive */ + 2
#define UNUSED_BACKSLASH \/* must not create a splice */
#if 0 && __COUNTER__ >= 0
not compiled
#endif
constexpr int counter=__COUNTER__;
constexpr char q[]="a\
    b//c";
constexpr char raw[]=u8R"tag(a
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
constexpr char ss[]=STR(alpha/**/beta);
static_assert(SUM(3)==5 && BLOCK==3);
static_assert(q[1]==' ' && q[5]=='b');
static_assert(raw[2]==' ' && raw[3]==' ' && raw[6]=='/');
static_assert(n==12345 && ss[5]==' ');
#ifdef LOCAL_BENCH
#error bench must be absent
#elif defined(FLAG)
constexpr int v=11;
#else
constexpr int v=12;
#endif
#if defined(FLAG)
#if defined(LOCAL_BENCH)
#error unreachable
#else
constexpr int w=21;
#endif
#elifndef LOCAL_BENCH
constexpr int w=22;
#else
#error unreachable
#endif
#if 0
#include <this//is/*not*/a/header>
#endif
static_assert(CLOCK_SCALE > 0);
int main(){return v+w+counter;}
'''.replace('constexpr char raw[]=u8R','constexpr char8_t raw[]=u8R')


def sha(data):return hashlib.sha256(data).hexdigest()
def tokens(data):return T.token_stream(data.decode('utf-8'))
def token_sha(t):return sha(json.dumps(t,ensure_ascii=False,separators=(',',':')).encode())
compilers={'gcc':['g++','-std=gnu++23','-O2','-march=native','-ftrivial-auto-var-init=zero'],
           'clang':['clang++','-std=gnu++23','-O2','-march=native','-stdlib=libc++','-ftrivial-auto-var-init=zero']}
env=os.environ.copy();env['SOURCE_DATE_EPOCH']='1794092400'
tool_hash=sha((R/'solutions/dcomp-notes/trim_tool.py').read_bytes())
report={'tool_sha256':tool_hash,'sizes':{},'versions':{},'fixtures':{},'production':{},'warning_counts':{}}

def pp(flags,data,tag,marker=False):
 cmd=flags+(['-D__LINE__=__TRIM_LINE_NUMBER__']if marker else[])+['-E','-P','-x','c++','-']
 p=subprocess.run(cmd,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 (TMP/(tag+'.pp.err')).write_bytes(p.stderr)
 if p.returncode:raise RuntimeError(tag+' preprocessing failed: '+p.stderr.decode()[-3000:])
 return tokens(p.stdout)

def equivalent(flags,original,new,tag,base_tokens=None):
 a=base_tokens if base_tokens is not None else pp(flags,original,tag+'-orig')
 b=pp(flags,new,tag+'-new')
 if a==b:return {'method':'-E -P exact tokens (literal payload and directive EOL retained)','tokens':len(a),'sha256':token_sha(a),'line_exceptions':0}
 # An independent marker pass locates the expansions of __LINE__. Validate that
 # this pass did not change any other token or preprocessor branch in either arm.
 am=pp(flags,original,tag+'-orig-mark',True);bm=pp(flags,new,tag+'-new-mark',True)
 if am!=bm:
  diff='\n'.join(difflib.unified_diff([repr(x)+'\n'for x in a],[repr(x)+'\n'for x in b],n=2))
  (D/(tag+'-mismatch.txt')).write_text(diff[:100000]);raise AssertionError(tag+' changed tokens')
 def check(real,marked):
  assert len(real)==len(marked),(tag,'marker changed token count')
  count=0
  for r,m in zip(real,marked):
   if r==m:continue
   assert m==('identifier','__TRIM_LINE_NUMBER__')and r[0]=='number'and r[1].isdigit(),(tag,r,m)
   count+=1
  return count
 ca,cb=check(a,am),check(b,bm);assert ca==cb
 return {'method':'-E -P tokens; only located __LINE__ expansions differ','tokens':len(am),'sha256':token_sha(am),'line_exceptions':ca}

def compile_one(flags,data,tag,syntax=False):
 cmd=flags+['-Wall','-fdiagnostics-color=never','-x','c++','-']+(['-fsyntax-only']if syntax else['-o',str(TMP/tag)])
 p=subprocess.run(cmd,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 (D/(tag+'.warnings.txt')).write_bytes(p.stderr)
 if p.returncode:raise RuntimeError(tag+' build failed: '+p.stderr.decode()[-4000:])
 # Line positions and caret drawings legitimately move. Compare diagnostic
 # messages/category, preserving message text and multiplicity.
 warnings=[re.sub(r'^.*?:\d+(?::\d+)?:\s*','',x)for x in p.stderr.decode().splitlines()if re.search(r'\bwarning:',x)]
 return warnings

# Small fixtures are intentionally adversarial: strings/raw bodies, escaped
# newlines, unknown branches, #elifndef, comments inside a #define, and pp-number.
(D/'fixture.cpp').write_text(FIXTURE)
fixture_stages={'original':FIXTURE,**dict(T.stages(FIXTURE))}
assert '    // text /* not a comment */'in fixture_stages['tabs']
assert '#ifndef CLOCK_SCALE\n#define CLOCK_SCALE 1.0\n#endif'in fixture_stages['production']
# Redefinitions must disable the global assumption instead of deleting live code.
redefine='#define LOCAL_BENCH 1\n#ifdef LOCAL_BENCH\nint x;\n#endif\n'
assert 'int x;'in T.prune_production(redefine)
for compiler,flags in compilers.items():
 report['versions'][compiler]=subprocess.check_output([flags[0],'--version'],text=True).splitlines()[0]
 for setting,extra in [('undef',[]),('defined',['-DFLAG=1','-DCLOCK_SCALE=1.1'])]:
  base=pp(flags+extra,FIXTURE.encode(),'fixture-base')
  for stage,s in fixture_stages.items():
   tag=f'fixture-{compiler}-{setting}-{stage}'
   report['fixtures'][tag]=equivalent(flags+extra,FIXTURE.encode(),s.encode(),tag,base)
   compile_one(flags+extra,s.encode(),tag,True)
 print('fixture passed',compiler,flush=True)

for short,name in [('time','dcomp-time-target'),('pace','jflags-pace-dual30')]:
 source=(D/(short+'-original.cpp')).read_bytes();text=source.decode()
 outputs={'original':text,**dict(T.stages(text))}
 report['sizes'][short]={k:len(v.encode())for k,v in outputs.items()}
 for stage,s in outputs.items():(D/(short+'-'+stage+'.cpp')).write_text(s)
 # Exercise the real public CLI's early stopping and its too-small-target exit.
 subprocess.run([sys.executable,'-B',str(R/'solutions/dcomp-notes/trim_tool.py'),str(D/(short+'-original.cpp')),'-o',str(D/(short+'-default.cpp')),'--report',str(D/(short+'-default.json')),'--force'],check=True)
 for compiler,flags in compilers.items():
  tag=f'{short}-{compiler}';base=pp(flags,source,tag+'-original');bw=compile_one(flags,source,tag+'-original')
  report['production'][tag]={};report['warning_counts'][tag]={'original':len(bw)}
  for stage,s in outputs.items():
   if stage=='original':continue
   q=equivalent(flags,source,s.encode(),tag+'-'+stage,base)
   warnings=compile_one(flags,s.encode(),tag+'-'+stage)
   assert sorted(warnings)==sorted(bw),(tag,stage,'new or changed warnings',bw,warnings)
   q['warnings_unchanged']=True;q['warnings']=len(warnings)
   report['production'][tag][stage]=q;report['warning_counts'][tag][stage]=len(warnings)
   print('verified',tag,stage,q,flush=True)
  # CLOCK_SCALE remains overridable in the production-pruned source.
  report['production'][tag]['clock_override']=equivalent(flags+['-DCLOCK_SCALE=1.1'],source,outputs['production'].encode(),tag+'-clock')
 (D/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
assert sha((R/'solutions/dcomp-notes/trim_tool.py').read_bytes())==tool_hash
report['complete']=True
(D/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('ALL TRIM VERIFICATIONS PASSED',flush=True)
