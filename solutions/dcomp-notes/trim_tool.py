#!/usr/bin/env python3
"""Safely trim a C++23 submission in the requested order.

Usage: python3 trim_tool.py INPUT -o OUTPUT [--target-bytes 515000]
Production contract: LOCAL_BENCH is undefined, and included headers do not
redefine it. CLOCK_SCALE guards are deliberately retained, including -D overrides.
Unknown preprocessor conditions are retained. No arbitrary macro evaluation occurs.
All transformations are also exposed through stages() for verification.
"""
from __future__ import annotations
import argparse
import bisect
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import sys


class TrimError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int
    end: int
    a: int
    b: int


# Phase 2, including GCC/Clang's accepted whitespace-before-newline extension.
SPLICE = re.compile(r'\\[ \t\v\f]*\r?\n')
RAW = re.compile(r'(?:u8|u|U|L)?R"([^\s()\\]{0,16})\(')
QUOTED = re.compile(r'(?:u8|u|U|L)?(["\'])')
IDENT = re.compile(r'(?:[A-Za-z_]|[^\x00-\x7f])(?:\w|[^\x00-\x7f])*')
PUNCT = sorted('%:%: >>= <<= <=> ->* ... ## :: .* -> ++ -- << >> <= >= == != && || += -= *= /= %= ^= &= |= <: :> <% %> %:'.split(),key=len,reverse=True)


def phase2(source: str):
    chars=[]; positions=[]; last=0
    for m in SPLICE.finditer(source):
        chars.append(source[last:m.start()]); positions.extend(range(last,m.start()));last=m.end()
    chars.append(source[last:]);positions.extend(range(last,len(source)))
    return ''.join(chars),positions


def lex(source: str) -> list[Token]:
    """Recognize literals/comments after splicing; raw bodies use physical bytes.

    Whitespace and comments are tokens too. Their separate treatment is needed
    for directive boundaries. Literal spellings are NEVER whitespace-normalized.
    """
    s,positions=phase2(source);n=len(s);i=0;out=[];recent=[]
    def emit(kind,a,b,physical_end=None):
        start=positions[a];end=positions[b-1]+1 if physical_end is None else physical_end
        out.append(Token(kind,source[start:end] if kind in ('literal','header') else s[a:b],start,end,a,b))
    while i<n:
        a=i
        if s[i].isspace():
            i+=1
            while i<n and s[i].isspace():i+=1
            emit('ws',a,i)
            if '\n'in s[a:i]:recent=[]
            continue
        if s.startswith('//',i):
            j=s.find('\n',i+2);i=n if j<0 else j;emit('comment',a,i);continue
        if s.startswith('/*',i):
            j=s.find('*/',i+2)
            if j<0:raise TrimError('unterminated block comment')
            i=j+2;emit('comment',a,i);continue
        m=RAW.match(s,i)
        if m:
            # Splicing is reverted inside raw literals. A split header is rare
            # and ambiguous to a lightweight lexer: fail closed, never guess.
            header=source[positions[a]:positions[m.end()-1]+1]
            if SPLICE.search(header):raise TrimError('spliced raw-string header is unsupported')
            close=')'+m.group(1)+'"';j=source.find(close,positions[m.end()-1]+1)
            if j<0:raise TrimError('unterminated raw string')
            end=j+len(close);i=bisect.bisect_left(positions,end)
            emit('literal',a,i,end);recent.append('<literal>');continue
        m=QUOTED.match(s,i)
        if m:
            quote=m.group(1);i=m.end()
            while i<n:
                if s[i]=='\\':i+=2;continue
                if s[i]==quote:i+=1;break
                if s[i]=='\n':raise TrimError('unescaped newline in quoted literal')
                i+=1
            else:raise TrimError('unterminated quoted literal')
            if i>n:raise TrimError('unterminated quoted escape')
            emit('literal',a,i);recent.append('<literal>');continue
        # Header names are preprocessing tokens, not comments or operators.
        is_header=(len(recent)==2 and recent[0]in ('#','%:')and recent[1]in ('include','include_next','import'))or(recent[-2:]in (['__has_include','('],['__has_include_next','(']))or(recent==['import'])
        if s[i]=='<'and is_header:
            j=s.find('>',i+1)
            if j<0 or '\n'in s[i:j]:raise TrimError('unterminated header name')
            i=j+1;emit('header',a,i);recent.append('<header>');continue
        if s[i].isdigit()or(s[i]=='.'and i+1<n and s[i+1].isdigit()):
            i+=1
            while i<n:
                c=s[i]
                if c.isalnum()or c in '_.':i+=1
                elif c=="'"and i+1<n and(s[i+1].isalnum()or s[i+1]=='_'):i+=2
                elif c in '+-'and s[i-1]in 'eEpP':i+=1
                else:break
            emit('number',a,i);recent.append(s[a:i]);continue
        m=IDENT.match(s,i)
        if m:i=m.end();kind='identifier'
        else:
            op=next((p for p in PUNCT if s.startswith(p,i)),s[i]);i+=len(op);kind='punct'
        emit(kind,a,i);recent.append(s[a:i])
    return out


def tab_indentation(source: str) -> str:
    protected=[(t.start,t.end)for t in lex(source)if t.kind in ('literal','header')]
    out=[];offset=0;j=0
    for original in source.splitlines(keepends=True):
        while j<len(protected)and protected[j][1]<=offset:j+=1
        m=re.match(r'[ \t]*',original);prefix=m.group()
        overlap=j<len(protected)and protected[j][0]<offset+len(prefix)and protected[j][1]>offset
        out.append(original if overlap else prefix.replace('    ','\t')+original[len(prefix):])
        offset+=len(original)
    return ''.join(out)


@dataclass
class Directive:
    kind: str
    args: list[str]
    start: int
    end: int
    keyword_start: int
    keyword_end: int


def directives(source: str) -> list[Directive]:
    logical,positions=phase2(source);rows=[];current=None;line_start=0;clean=True
    for t in lex(source):
        if t.kind=='ws':
            if '\n'in t.text:
                first=t.a+t.text.index('\n');last=t.a+t.text.rindex('\n')
                if current:
                    tokens,start=current
                    if len(tokens)>1:
                        k=tokens[1];rows.append(Directive(k.text,[x.text for x in tokens[2:]],start,positions[first]+1,k.start,k.end))
                    current=None
                line_start=positions[last]+1;clean=True
            continue
        if t.kind=='comment':continue
        if clean and t.text in ('#','%:'):current=([t],line_start)
        elif current:current[0].append(t)
        clean=False
    if current and len(current[0])>1:
        toks,start=current;k=toks[1];rows.append(Directive(k.text,[x.text for x in toks[2:]],start,len(source),k.start,k.end))
    return rows


# Three-valued Boolean subset. Unknown arithmetic/macros stay verbatim.
def condition(d: Directive, local_known_undefined: bool):
    if d.kind in ('ifdef','ifndef','elifdef','elifndef'):
        if d.args==['LOCAL_BENCH']and local_known_undefined:return d.kind in ('ifndef','elifndef')
        return None
    ts=d.args;pos=0
    def unary():
        nonlocal pos
        if pos>=len(ts):raise TrimError('incomplete #if')
        x=ts[pos];pos+=1
        if x=='!':
            v=unary();return None if v is None else not v
        if x=='(':
            v=expr_or()
            if pos>=len(ts)or ts[pos]!=')':raise TrimError('unsupported #if')
            pos+=1;return v
        if x=='defined':
            paren=pos<len(ts)and ts[pos]=='('
            if paren:pos+=1
            if pos>=len(ts)or not re.fullmatch(r'[A-Za-z_]\w*',ts[pos]):raise TrimError('unsupported defined')
            name=ts[pos];pos+=1
            if paren:
                if pos>=len(ts)or ts[pos]!=')':raise TrimError('unsupported defined')
                pos+=1
            return False if name=='LOCAL_BENCH'and local_known_undefined else None
        if x=='LOCAL_BENCH'and local_known_undefined:return False
        if re.fullmatch(r'[0-9]+[uUlL]*',x):return int(re.sub('[uUlL]+$','',x))!=0
        # Do not fold expressions containing expandable unknown macros: even
        # an apparently unused __COUNTER__ expansion could have side effects.
        raise TrimError('unknown #if expression')
    def expr_and():
        nonlocal pos
        v=unary()
        while pos<len(ts)and ts[pos]=='&&':
            pos+=1;w=unary();v=False if v is False or w is False else True if v is True and w is True else None
        return v
    def expr_or():
        nonlocal pos
        v=expr_and()
        while pos<len(ts)and ts[pos]=='||':
            pos+=1;w=expr_and();v=True if v is True or w is True else False if v is False and w is False else None
        return v
    try:
        v=expr_or();return v if pos==len(ts)else None
    except TrimError:return None


@dataclass
class Branch:
    header: Directive
    body: list = field(default_factory=list)


@dataclass
class Conditional:
    branches: list[Branch] = field(default_factory=list)
    close: Directive|None = None


def prune_production(source: str) -> str:
    ds=directives(source)
    # If the source changes LOCAL_BENCH itself, its value is no longer a global
    # build assumption. Keep every such condition rather than guessing dataflow.
    known=not any(d.kind in ('define','undef')and d.args and d.args[0]=='LOCAL_BENCH'for d in ds)
    root=[];cur=root;stack=[];pos=0
    for d in ds:
        if d.kind not in ('if','ifdef','ifndef','elif','elifdef','elifndef','else','endif'):continue
        cur.append(source[pos:d.start]);pos=d.end
        if d.kind in ('if','ifdef','ifndef'):
            node=Conditional([Branch(d)]);cur.append(node);stack.append((node,cur));cur=node.branches[-1].body
        elif d.kind in ('elif','elifdef','elifndef','else'):
            if not stack:raise TrimError('unmatched #'+d.kind)
            node,parent=stack[-1]
            if node.branches[-1].header.kind=='else':raise TrimError('branch after #else')
            node.branches.append(Branch(d));cur=node.branches[-1].body
        else:
            if not stack:raise TrimError('unmatched #endif')
            node,cur=stack.pop();node.close=d
    if stack:raise TrimError('unterminated conditional')
    cur.append(source[pos:])
    def blank(text):return '\n'*text.count('\n')
    def text(d):return source[d.start:d.end]
    def body_span(b,end):return source[b.header.end:end]
    def rewrite(d,kind):
        return source[d.start:d.keyword_start]+kind+source[d.keyword_end:d.end]
    def render(nodes):
        out=[]
        for node in nodes:
            if isinstance(node,str):out.append(node);continue
            close=node.close;live=[];possible=True
            for i,b in enumerate(node.branches):
                v=True if b.header.kind=='else'else condition(b.header,known)
                end=node.branches[i+1].header.start if i+1<len(node.branches)else close.start
                if not possible or v is False:
                    live.append(('dead',b,end));continue
                live.append(('true'if v is True else'unknown',b,end))
                if v is True:possible=False
            kept=[x for x in live if x[0]!='dead']
            sole=len(kept)==1 and kept[0][0]=='true'
            seen=False
            for typ,b,end in live:
                if typ=='dead':out.append(blank(text(b.header)+body_span(b,end)));continue
                if sole:out.append(blank(text(b.header)))
                elif not seen:
                    out.append(rewrite(b.header,{'elif':'if','elifdef':'ifdef','elifndef':'ifndef'}[b.header.kind])if b.header.kind in ('elif','elifdef','elifndef')else text(b.header));seen=True
                elif typ=='true'and b.header.kind in ('elif','elifdef','elifndef'):
                    # Its proven-true expression contains only constants and
                    # defined tests: no expansion side effects are removed.
                    out.append('#else\n'+blank(text(b.header)).removeprefix('\n'))
                else:out.append(text(b.header))
                out.append(render(b.body))
            out.append(text(close)if kept and not sole else blank(text(close)))
        return ''.join(out)
    result=render(root)
    # Parse the result too; errors never result in a written output file.
    directives(result)
    return result


def remove_comments(source: str) -> str:
    out=[];origin=[];pos=0
    for t in lex(source):
        if t.kind!='comment':continue
        out.extend((source[pos:t.start],' '));origin.extend(range(pos,t.start));origin.append(-1);pos=t.end
    out.append(source[pos:]);origin.extend(range(pos,len(source)));result=''.join(out)
    # An empty comment is occasionally needed as a physical barrier. Otherwise
    # \ followed by a removed comment and a newline could become a new splice.
    barriers=[]
    for m in SPLICE.finditer(result):
        old=origin[m.start()]
        if old<0 or not SPLICE.match(source,old):barriers.append(m.start()+1)
    for pos in reversed(barriers):result=result[:pos]+'/**/'+result[pos:]
    lex(result)
    return result


def stages(source: str):
    for label,fn in [('tabs',tab_indentation),('production',prune_production),('comments',remove_comments)]:
        source=fn(source);yield label,source


def token_stream(source: str):
    """Strict whitespace normalization, retaining literal bytes and pragma EOLs.

    Retaining one whitespace separator (rather than dropping all whitespace)
    also distinguishes a user-defined literal from a literal plus an identifier.
    """
    result=[];directive=False;clean=True
    for t in lex(source):
        if t.kind=='comment':
            if result and result[-1][0]!='ws':result.append(('ws',' '))
            continue
        if t.kind=='ws':
            if '\n'in t.text:
                if directive:
                    if result and result[-1][0]=='ws':result.pop()
                    result.append(('directive-end','\n'))
                directive=False;clean=True
            if result and result[-1][0]not in ('ws','directive-end'):result.append(('ws',' '))
            continue
        if clean and t.text in ('#','%:'):directive=True
        result.append((t.kind,t.text));clean=False
    if result and result[-1][0]=='ws':result.pop()
    if directive:result.append(('directive-end','\n'))
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input',type=Path);p.add_argument('-o','--output',required=True,type=Path)
    p.add_argument('--target-bytes',type=int,default=515000)
    p.add_argument('--report',type=Path);p.add_argument('--force',action='store_true')
    a=p.parse_args(argv)
    if a.input.resolve()==a.output.resolve():p.error('input and output must differ')
    if a.output.exists()and not a.force:p.error('output exists; use --force explicitly')
    if a.report and a.report.resolve()in (a.input.resolve(),a.output.resolve()):p.error('report must differ from input and output')
    if a.report and a.report.exists()and not a.force:p.error('report exists; use --force explicitly')
    if a.target_bytes<=0:p.error('--target-bytes must be positive')
    raw=a.input.read_bytes();source=raw.decode('utf-8');sizes={'input':len(raw)};applied=[]
    if len(raw)>a.target_bytes:
        for label,source in stages(source):
            sizes[label]=len(source.encode('utf-8'));applied.append(label)
            if sizes[label]<=a.target_bytes:break
    data=source.encode('utf-8');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
    report={'input':str(a.input),'output':str(a.output),'sizes':sizes,'applied':applied,
            'target_bytes':a.target_bytes,'target_met':len(data)<=a.target_bytes,'atcoder_limit_met':len(data)<=524288,
            'input_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(data).hexdigest()}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2),file=sys.stderr)
    if not report['target_met']:
        print('All three steps finished, but the target is not met. Stop here; no further changes made.',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (TrimError,UnicodeError)as e:print('trim_tool: '+str(e),file=sys.stderr);raise SystemExit(1)
