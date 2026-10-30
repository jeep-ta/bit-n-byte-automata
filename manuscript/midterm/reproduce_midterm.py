"""Reproduce the retained Prelim and Midterm evidence."""
from pathlib import Path
import sys,json,csv,platform,time,statistics,tracemalloc,hashlib
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tests.scenarios import SOURCE
from tests.midterm_scenarios import run_midterm_cases
from bpsl.grammar import Grammar,BPSL,analysis,parse_stack,simplify,cnf,gnf,cyk
from bpsl.compiler import compile_source,lex
from bpsl.labs import regex_lab
OUT=Path(__file__).resolve().parent/'evidence';OUT.mkdir(exist_ok=True)

def main():
    rows=run_midterm_cases()
    balanced=Grammar('S',{'S':{('a','S','b'),()}})
    def deep():
        result=parse_stack(list('a'*40+'b'*40),balanced)
        return [result['accepted'],max(len(x['stack_before']) for x in result['trace'])]
    regex=regex_lab()
    from bpsl.automata import thompson
    d=thompson('(a|b)*abb').determinize()[0]
    witnesses=[('','a','bb'),('','ab','b'),('','abb',''),('a','ab','b'),('a','abb',''),('ab','abb','')]
    from bpsl.automata import minimize
    minimized=minimize(d)[0]
    comparisons=[]
    for word,expected in [('aabb',True),('abb',True),('aba',False),('',False)]:
        original_result=d.simulate(word);small_result=minimized.simulate(word)
        assert (original_result['classification']=='CONFORMING')==expected
        assert (small_result['classification']=='CONFORMING')==expected
        comparisons.append(dict(word=word,expected=expected,original=original_result,minimized=small_result))
    (OUT/'acceptance_comparison.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
    date=datetime.now(timezone(timedelta(hours=8))).isoformat()
    for row in rows:
        row.update(requirement=row['id'].split('-')[0],module='automata.py' if row['id'] in ['MT-07','MT-08'] else 'grammar.py' if row['id'].startswith(('CFG','PDA','MT')) else 'See scenario and source module map',
                   formal_input=row.get('input',row.get('input_definition',row['scenario'])),
                   tester='Automated by Codex; member review not asserted',date=date,
                   defect_identified='None in this run' if row['status']=='PASS' else 'Expected/actual mismatch',
                   corrective_action='Not required in this run' if row['status']=='PASS' else 'Investigate',
                   retest_result='Not applicable; initial recorded pass' if row['status']=='PASS' else 'Pending')
    passed=sum(r['status']=='PASS' for r in rows)
    summary=dict(date=date,python=platform.python_version(),platform=platform.platform(),scope='Prelim regression and Midterm grammar/PDA only',scenarios=len(rows),passed=passed,failed=len(rows)-passed,results=rows)
    (OUT/'tests.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    keys=['id','scenario','requirement','module','formal_input','expected','actual','status','tester','date','defect_identified','corrective_action','retest_result']
    with (OUT/'tests.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader()
        for row in rows:w.writerow({k:json.dumps(row[k],ensure_ascii=True) if isinstance(row.get(k),(list,dict)) else row.get(k,'') for k in keys})
    artifact=compile_source(SOURCE);kinds=[t.kind for t in lex(SOURCE)[:-1]]
    gs={'original':BPSL,'simplified':simplify(BPSL)[0],'cnf':cnf(BPSL)[0],'gnf':gnf(BPSL)[0]}
    grammars={name:dict(start=g.start,rules={v:[list(r) for r in sorted(rs)] for v,rs in g.rules.items()},display=g.display(),variables=len(g.variables),terminals=len(g.terminals),productions=sum(len(rs) for rs in g.rules.values())) for name,g in gs.items()}
    first,follow,_,conflicts=analysis(BPSL)
    def nodes(tree):return 1+sum(nodes(c) for c in tree['children'])
    formal=dict(source=SOURCE,model=artifact['model'].table(),tokens=artifact['tokens'],parsed=artifact['parsed'],findings=artifact['findings'],regex=regex,
                grammars=grammars,simplification_log=simplify(BPSL)[1],cnf_log=cnf(BPSL)[1],gnf_log=gnf(BPSL)[1],
                first={k:sorted(v) for k,v in first.items()},follow={k:sorted(v) for k,v in follow.items()},conflicts=conflicts,
                metrics=dict(tokens=len(kinds),pda_steps=len(artifact['parsed']['pda']['trace']),tree_nodes=nodes(artifact['parsed']['tree']),
                             leftmost_steps=len(artifact['parsed']['leftmost'])-1,rightmost_steps=len(artifact['parsed']['rightmost'])-1,
                             max_stack=max(len(x['stack_before']) for x in artifact['parsed']['pda']['trace'])),
                balanced=dict(grammar=balanced.display(),word='aabb',result=parse_stack(list('aabb'),balanced),deep_result=deep()),witnesses=witnesses)
    (OUT/'formal_artifacts.json').write_text(json.dumps(formal,indent=2),encoding='utf-8')
    measures=[]
    for name,op in [('simplify',lambda:simplify(BPSL)),('cnf',lambda:cnf(BPSL)),('gnf',lambda:gnf(BPSL)),('predictive_parse',lambda:parse_stack(kinds)),('cyk_membership',lambda:cyk(gs['cnf'],kinds))]:
        op();times=[]
        for _ in range(7):
            t=time.perf_counter_ns();value=op();times.append((time.perf_counter_ns()-t)/1e6);del value
        tracemalloc.start();op();_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        measures.append(dict(operation=name,trials=7,times_ms=times,median_ms=statistics.median(times),minimum_ms=min(times),maximum_ms=max(times),peak_python_kib=peak/1024))
    (OUT/'performance.json').write_text(json.dumps(dict(date=date,python=platform.python_version(),platform=platform.platform(),cpu='Intel Core i5-8400 @ 2.80 GHz',physical_memory_bytes=17129119744,input='Reference BPSL grammar; procurement source; 65 non-EOF token categories',method='One warm-up; 7 perf_counter_ns trials; separate tracemalloc peak run; no outliers removed',results=measures),indent=2),encoding='utf-8')
    source_files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.parts[len(ROOT.parts)] in ['bpsl','tests','samples'] and '__pycache__' not in p.parts and p.suffix!='.pyc')
    source_files += [ROOT/n for n in ['main.py','README.md','run_tests.py','benchmark.py','requirements.txt','.gitignore']]
    source_files.append(Path(__file__).resolve())
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    (OUT/'source_manifest.json').write_text(json.dumps(dict(date=date,files=hashes,scope='Application source and manuscript cover retained Prelim and Midterm work only'),indent=2),encoding='utf-8')
    assert len(rows)==109 and passed==109,summary
    print(f'{passed}/{len(rows)} midterm records passed; metrics: {formal["metrics"]}')

if __name__=='__main__':main()
