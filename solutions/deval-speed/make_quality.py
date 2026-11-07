"""Create isolated experiments; unchanged guards and fixed request budgets."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
base=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
def write(name,code,description):
    d=ROOT/'solutions'/name;d.mkdir(exist_ok=True)
    (d/'main.cpp').write_text(code)
    (d/'README.md').write_text(f'# {name}\n\n改良元: solutions/deval-vbranch-o3。\n\n{description}\n\n時間ガード、DesignStore、@paper/@opsは維持。LOCAL_BENCHでは注文探索予算は固定。\n')
    print(name,len(code.encode()))
for samples in (16,8):
    s=base.replace('static constexpr int kSamples = 32;',f'static constexpr int kSamples = {samples};',1)
    write(f'deval-perf{samples}',s,f'穴あけの期待利益を測る層化サンプル数を32から{samples}に減らす。他の設計段・選択V・注文処理は同じ。')
for tag,settings in [
    ('reqpost5',{'POST_CANDIDATES':5}),
    ('reqround3',{'NS_ROUNDS':3}),
    ('reqvalue',{'CANDIDATE_PRIORITY':0}),
    ('reqhidden0',{'HIDDEN_RANK':0}),
    ('reqshort0',{'PLAN_SHORTLIST':0}),
    ('reqanchors1',{'ONE_ANCHORS':1}),
]:
    extra='        if(const char* explicit_value=std::getenv(local.c_str()))return explicit_value;\n'
    for k,v in settings.items():extra+=f'        if(std::strcmp(name,"{k}")==0)return "{v}";\n'
    s=base.replace('        return std::getenv(local.c_str());',extra+'        return nullptr;',1)
    write('deval-'+tag,s,'注文探索の既定設定だけを変更: '+str(settings)+'。F3_*環境変数で上書きできる。設計段は変更しない。')
