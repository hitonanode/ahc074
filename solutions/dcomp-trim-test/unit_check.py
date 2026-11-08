from pathlib import Path
import sys,ast,importlib.util,json,subprocess
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parents[1]
spec=importlib.util.spec_from_file_location('trim_tool',R/'solutions/dcomp-notes/trim_tool.py');T=importlib.util.module_from_spec(spec);sys.modules[spec.name]=T;spec.loader.exec_module(T)
node=next(n for n in ast.parse((D/'verify.py').read_text()).body if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='FIXTURE').value
fixture=ast.literal_eval(node.func.value).replace(*(ast.literal_eval(a)for a in node.args))
literals=lambda s:[t.text for t in T.lex(s)if t.kind=='literal']
orig=literals(fixture)
for step,s in T.stages(fixture):
 assert literals(s)==orig,(step,'literal changed')
 if step=='production':assert '#ifndef CLOCK_SCALE\n#define CLOCK_SCALE 1.0\n#endif'in s
(D/'unit-fixture.cpp').write_text(fixture)
cmd=[sys.executable,'-B',str(R/'solutions/dcomp-notes/trim_tool.py'),str(D/'unit-fixture.cpp'),'-o',str(D/'unit-too-small.cpp'),'--target-bytes','1','--force']
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==2,p.stderr
assert(D/'unit-too-small.cpp').read_text()==s
before=(D/'unit-fixture.cpp').read_bytes()
p=subprocess.run(cmd+['--report',str(D/'unit-fixture.cpp')],capture_output=True,text=True);assert p.returncode!=0
assert(D/'unit-fixture.cpp').read_bytes()==before
# Preprocessor expressions may have side effects: leave unknown ones unchanged.
for q in ['#if X && defined(LOCAL_BENCH)\nint x;\n#endif\n','#define LOCAL_BENCH 1\n#ifdef LOCAL_BENCH\nint x;\n#endif\n']:
 assert T.prune_production(q)==q
for q in ['#ifdef LOCAL_BENCH\nint x;\n#else\nint y;\n#endif\n','#if defined(FLAG) && defined(LOCAL_BENCH)\nint x;\n#else\nint y;\n#endif\n']:
 result=T.prune_production(q);assert'int x;'not in result and'int y;'in result
for q in ['#if 0\n#if 1\n#endif\n','#else\n']:
 try:T.prune_production(q)
 except T.TrimError:pass
 else:raise AssertionError('malformed nesting accepted')
print('unit checks passed: literal preservation, CLOCK_SCALE, conservative conditionals, exit status and non-destructive output')
