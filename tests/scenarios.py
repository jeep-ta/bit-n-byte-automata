from pathlib import Path
from itertools import product
from bpsl.compiler import lex, parse, compile_source, Diagnostic, identifier_automata
from bpsl.automata import DFA, NFA, thompson, minimize, equivalent
from bpsl.grammar import Grammar, BPSL, analysis, simplify, cnf, gnf, cyk, parse_stack, derivation
from bpsl.labs import grammar_lab

SOURCE = (Path(__file__).resolve().parents[1] / 'samples/procurement.bpsl').read_text(encoding='utf-8')


def run_cases():
    records = []
    def check(id, scenario, expected, operation):
        import inspect
        try:
            input_definition = inspect.getsource(operation).strip()
            import json
            closure = inspect.getclosurevars(operation)
            bindings = {}
            captured = {**closure.globals, **closure.nonlocals}
            captured.update({k:p.default for k,p in inspect.signature(operation).parameters.items()
                             if p.default is not inspect.Parameter.empty})
            for name, value in captured.items():
                if callable(value):
                    continue
                if hasattr(value, 'table'):
                    value = value.table()
                elif hasattr(value, 'display'):
                    value = value.display()
                bindings[name] = value
            input_definition += '\nBound inputs: ' + json.dumps(bindings, default=repr, ensure_ascii=True)
        except (OSError, TypeError):
            input_definition = scenario
        try:
            actual = operation()
        except Exception as e:
            actual = f'UNEXPECTED {type(e).__name__}: {e}'
        records.append(dict(id=id, scenario=scenario, expected=expected, actual=actual,
                            status='PASS' if actual == expected else 'FAIL', input_definition=input_definition))
    def stage(source):
        try:
            compile_source(source)
            return 'OK'
        except Diagnostic as e:
            return e.stage
    model = compile_source(SOURCE)['model']
    check('LEX-01','Reserved keyword precedence','PROCESS',lambda:lex('PROCESS')[0].kind)
    check('LEX-02','Identifier token and spelling',['IDENTIFIER','Procurement'],lambda:[lex('Procurement')[0].kind,lex('Procurement')[0].lexeme])
    check('LEX-03','Digit-leading fragment rejected','LEXICAL',lambda:stage(SOURCE.replace('Procurement','2Procurement')))
    check('LEX-04','Unknown symbol rejected','LEXICAL',lambda:stage(SOURCE.replace('STATE Requested;','STATE @;')))
    check('LEX-05','Spaces tabs CRLF preserve token categories',True,lambda:[t.kind for t in lex(SOURCE)]==[t.kind for t in lex(SOURCE.replace(' ', '\t').replace('\n','\r\n'))])
    check('LEX-06','Longest keyword-prefix identifier',['IDENTIFIER','PROCESSX'],lambda:[lex('PROCESSX')[0].kind,lex('PROCESSX')[0].lexeme])
    check('LEX-07','Underscore and digit suffix','_State2',lambda:lex('_State2')[0].lexeme)
    check('LEX-08','Case-sensitive keyword policy','IDENTIFIER',lambda:lex('process')[0].kind)
    def location():
        try: lex('\n  @')
        except Diagnostic as e: return [e.line,e.column]
    check('LEX-09','Source error location',[2,3],location)
    check('LEX-10','Production identifier DFA rejects invalid words',[True,True,False,False],lambda:[identifier_automata()[2].simulate(w)['classification']=='CONFORMING' for w in ['A','_x2','2x','']])
    check('PAR-01','Complete procurement syntax','OK',lambda:stage(SOURCE))
    for id, name, text in [
        ('PAR-02','Missing semicolon',SOURCE.replace('STATE Requested;','STATE Requested')),
        ('PAR-03','Missing closing brace',SOURCE[:-2]),
        ('PAR-04','Transition missing ON',SOURCE.replace(' ON approve',' approve')),
        ('PAR-05','Transition missing TO',SOURCE.replace(' TO Approved',' Approved')),
        ('PAR-06','Unexpected trailing token',SOURCE+' x'),
        ('PAR-07','Two process blocks',SOURCE+SOURCE),
        ('PAR-08','Empty source',''),
        ('PAR-09','Misplaced delimiter',SOURCE.replace('STATE Requested;','STATE { Requested;'))]:
        check(id,name,'SYNTAX',lambda text=text:stage(text))
    for id,name,text in [
        ('STR-01','Undeclared START state',SOURCE.replace('START Requested','START Missing')),
        ('STR-02','Undeclared ACCEPT state',SOURCE.replace('ACCEPT Completed','ACCEPT Missing')),
        ('STR-03','Undeclared transition event',SOURCE.replace('ON approve','ON refund')),
        ('STR-04','Conflicting same source and event',SOURCE.replace('}', 'TRANSITION Requested ON approve TO Paid; }')),
        ('STR-05','Duplicate STATE',SOURCE.replace('}', 'STATE Requested; }')),
        ('STR-06','Duplicate EVENT',SOURCE.replace('}', 'EVENT approve; }')),
        ('STR-07','Missing START',SOURCE.replace('START Requested;','')),
        ('STR-08','Missing ACCEPT',SOURCE.replace('ACCEPT Completed;','')),
        ('STR-09','Two START declarations',SOURCE.replace('}', 'START Approved; }')),
        ('STR-10','Undeclared transition source',SOURCE.replace('TRANSITION Requested','TRANSITION Missing')),
        ('STR-11','Undeclared transition destination',SOURCE.replace('TO Approved','TO Missing')),
        ('STR-12','Duplicate identical transition',SOURCE.replace('}', 'TRANSITION Requested ON approve TO Approved; }')),
        ('STR-13','Duplicate ACCEPT',SOURCE.replace('}', 'ACCEPT Completed; }')),
        ('STR-14','Syntactically valid empty block is structurally invalid','PROCESS Empty {}'),
        ('STR-15','No events declared','PROCESS X { STATE A; START A; ACCEPT A; }')]:
        check(id,name,'STRUCTURAL',lambda text=text:stage(text))
    check('STR-16','Forward references allowed','OK',lambda:stage('PROCESS X { START A; ACCEPT B; TRANSITION A ON e TO B; STATE A; STATE B; EVENT e; }'))
    check('STR-17','State/event namespaces separate','OK',lambda:stage('PROCESS X { STATE A; EVENT A; START A; ACCEPT A; TRANSITION A ON A TO A; }'))
    check('PROC-01','Exact procurement model',[5,4,4,'Requested',['Completed']],lambda:[len(model.states),len(model.alphabet),len(model.transitions),model.start,sorted(model.accepts)])
    check('CONF-01','Full valid trace',['CONFORMING','Completed',['Requested','Approved','Purchased','Paid','Completed']],lambda:[model.simulate('approve purchase pay complete'.split())[k] for k in ['classification','final','trace']])
    check('CONF-02','Skipped purchase',['NONCONFORMING',2,'Approved','pay',['purchase']],lambda:[model.simulate('approve pay complete'.split())[k] for k in ['classification','position','final','observed','permitted']])
    check('CONF-03','Valid prefix incomplete',['INCOMPLETE','Purchased'],lambda:[model.simulate(['approve','purchase'])[k] for k in ['classification','final']])
    check('CONF-04','Unknown event',['NONCONFORMING',2,'unknown event'],lambda:[model.simulate(['approve','refund'])[k] for k in ['classification','position','reason']])
    alternative=SOURCE.replace('}', 'TRANSITION Requested ON complete TO Completed; }')
    check('CONF-05','Explicit alternative path','CONFORMING',lambda:compile_source(alternative)['model'].simulate(['complete'])['classification'])
    check('CONF-06','Empty events in nonaccepting start',['INCOMPLETE',['Requested']],lambda:[model.simulate([])[k] for k in ['classification','trace']])
    check('CONF-07','Empty events in accepting start','CONFORMING',lambda:compile_source(SOURCE.replace('ACCEPT Completed','ACCEPT Requested'))['model'].simulate([])['classification'])
    check('CONF-08','First event invalid',[1,'Requested'],lambda:[model.simulate(['purchase'])[k] for k in ['position','final']])
    check('CONF-09','Extra event after completion',[5,'Completed',[]],lambda:[model.simulate('approve purchase pay complete pay'.split())[k] for k in ['position','final','permitted']])
    check('VIOL-01','Valid prefix and last state retained',[['approve'],'Approved'],lambda:[model.simulate(['approve','pay'])[k] for k in ['valid_prefix','final']])
    isolated=SOURCE.replace('}', 'STATE Isolated; ACCEPT Isolated; }')
    check('REACH-01','Unreachable state reported',['Isolated'],lambda:compile_source(isolated)['findings']['unreachable'])
    check('REACH-02','Unreachable accept reported',['Isolated'],lambda:compile_source(isolated)['findings']['unreachable_accepts'])
    check('REACH-03','Reachable cycle terminates',5,lambda:len(compile_source(SOURCE.replace('}', 'TRANSITION Completed ON approve TO Requested; }'))['findings']['reachable']))
    check('AUT-01','Literal regex recognizes only a',[False,True,False],lambda:[thompson('a').accepts_word(w) for w in ['', 'a','aa']])
    check('AUT-02','Epsilon closure includes chained branching cycle',[0,1,2,3],lambda:sorted(NFA({0,1,2,3},{}, {(0,None):{1,2},(1,None):{3},(3,None):{0}},0,{3},[]).closure({0})))
    check('AUT-03','NFA/subset independent simulation: all binary words length <= 5',True,
          lambda:all(thompson('(a|b)*abb').accepts_word(w)==(thompson('(a|b)*abb').determinize()[0].simulate(w)['classification']=='CONFORMING') for n in range(6) for w in map(''.join,product('ab',repeat=n))))
    check('AUT-04','DFA accepts aabb','CONFORMING',lambda:thompson('(a|b)*abb').determinize()[0].simulate('aabb')['classification'])
    check('AUT-05','DFA rejects aba',False,lambda:thompson('(a|b)*abb').determinize()[0].simulate('aba')['classification']=='CONFORMING')
    merge=DFA({'s','p','q','f','unreachable'},{'a','b'},{('s','a'):'p',('s','b'):'q',('p','a'):'f',('q','a'):'f'},'s',{'f'})
    check('AUT-06','Minimization merges equivalent states',True,lambda:any({'p','q'}<=set(g) for g in minimize(merge)[1]['classes'].values()))
    check('AUT-07','Minimization removes unreachable state',['unreachable'],lambda:minimize(merge)[1]['removed_unreachable'])
    check('AUT-08','Complete product equivalence after minimization',True,lambda:equivalent(merge,minimize(merge)[0])['equivalent'])
    check('AUT-09','Complete equivalence returns shortest witness',['a'],lambda:equivalent(thompson('a').determinize()[0],thompson('b').determinize()[0])['counterexample'])
    check('AUT-10','Equivalence finds empty-string witness',[],lambda:equivalent(thompson('a*').determinize()[0],thompson('a+').determinize()[0])['counterexample'])
    for i,(pattern,words,expected) in enumerate([
        ('a|b',['a','b','ab',''],[True,True,False,False]),
        ('ab',['a','ab','ba'],[False,True,False]),
        ('a*',['','a','aa','b'],[True,True,True,False]),
        ('a+',['','a','aa'],[False,True,True]),
        ('a?',['','a','aa'],[True,True,False]),
        ('(ab)*',['','ab','abab','aba'],[True,True,True,False]),
        ('ε',['','a'],[True,False]),
        ('',['','a'],[True,False]),
        ('\\*',['*',''],[True,False])],11):
        check(f'AUT-{i:02}',f'Regex {pattern!r}: {words}',expected,lambda p=pattern,ws=words:[thompson(p).accepts_word(w) for w in ws])
    def badregex(pattern):
        try: thompson(pattern); return 'OK'
        except ValueError: return 'REGEX ERROR'
    for i,p in enumerate(['(',')','a|','|a','*a','a\\','()'],20):
        check(f'AUT-{i:02}',f'Malformed regex {p!r}','REGEX ERROR',lambda p=p:badregex(p))
    check('CFG-01','BPSL has no LL(1) conflicts',[],lambda:analysis(BPSL)[3])
    kinds=[t.kind for t in lex(SOURCE)[:-1]]
    tree=parse_stack(kinds)['tree']
    check('CFG-02','Leftmost derivation ends at actual token categories',kinds,lambda:derivation(tree)[-1])
    check('CFG-03','Rightmost derivation ends at actual token categories',kinds,lambda:derivation(tree,True)[-1])
    def leaves(node):
        return sum((leaves(c) for c in node['children']),[]) if node['symbol'] in BPSL.variables else [node['symbol']]
    check('CFG-04','Parse-tree terminal yield',kinds,lambda:leaves(tree))
    toy=Grammar('S',{'S':{('A','B'),('U',)},'A':{(),('a',)},'B':{('b',)},'U':{('V',)},'V':{('a',)},'Dead':{('Dead',)}})
    simple,steps=simplify(toy)
    check('CFG-05','Simplification removes non-start epsilon rules',True,lambda:all(() not in rs for v,rs in simple.rules.items() if v!=simple.start))
    check('CFG-06','Simplification removes unit productions',True,lambda:all(not(len(r)==1 and r[0] in simple.variables) for rs in simple.rules.values() for r in rs))
    check('CFG-07','Useless symbols removed',False,lambda:'Dead' in simple.rules)
    normal=cnf(BPSL)[0]
    check('CFG-08','Every CNF production has prescribed form',True,lambda:all((len(r)==1 and r[0] in normal.terminals) or (len(r)==2 and all(x in normal.variables for x in r)) or (not r and v==normal.start) for v,rs in normal.rules.items() for r in rs))
    check('CFG-09','CNF/CYK independently accepts procurement token stream',True,lambda:cyk(normal,kinds))
    check('CFG-10','CNF/CYK rejects missing semicolon',False,lambda:cyk(normal,[t.kind for t in lex(SOURCE.replace('STATE Requested;','STATE Requested'))[:-1]]))
    greibach=gnf(BPSL)[0]
    check('CFG-11','Every BPSL GNF production is terminal then variables',True,lambda:all((not r and v==greibach.start) or (bool(r) and r[0] in greibach.terminals and all(x in greibach.variables for x in r[1:])) for v,rs in greibach.rules.items() for r in rs))
    def gnf_accept(g,words):
        # Independent bounded nondeterministic GNF stack search; one terminal per step.
        stacks={(g.start,)}
        for a in words:
            stacks={r[1:]+stack[1:] for stack in stacks if stack for r in g.rules[stack[0]] if r and r[0]==a}
        return () in stacks or (not words and () in g.rules[g.start])
    check('CFG-12','GNF accepts actual procurement tokens',True,lambda:gnf_accept(greibach,kinds))
    check('CFG-13','GNF rejects malformed procurement tokens',False,lambda:gnf_accept(greibach,kinds[:-1]))
    epsilon=Grammar('S',{'S':{(),('a','S')}})
    enormal=cnf(epsilon)[0]
    check('CFG-14','CNF preserves epsilon and repetition',[True,True,True,False],lambda:[cyk(enormal,w) for w in [[],['a'],['a','a'],['b']]])
    def gnf_cycle():
        try: gnf(Grammar('S',{'S':{('S','a'),('b',)}})); return 'OK'
        except ValueError: return 'UNSUPPORTED LEADING CYCLE'
    check('CFG-15','GNF scope guard reports left recursion','UNSUPPORTED LEADING CYCLE',gnf_cycle)
    check('CFG-16','Simplified toy CNF preserves manually enumerated language',[False,True,True,True,False],lambda:[cyk(cnf(toy)[0],list(w)) for w in ['','a','b','ab','aa']])
    check('PDA-01','Valid full BPSL accepted by stack machine',True,lambda:parse_stack(kinds)['accepted'])
    check('PDA-02','Malformed BPSL rejected by stack machine',False,lambda:parse_stack(kinds[:-1])['accepted'])
    check('PDA-03','Acceptance requires exhausted input',False,lambda:parse_stack(kinds+['IDENTIFIER'])['accepted'])
    check('PDA-04','Stack trace ends empty',[],lambda:parse_stack(kinds)['trace'][-1]['stack_after'])
    check('PDA-05','Grammar accepts empty declaration list syntax',True,lambda:parse_stack(['PROCESS','IDENTIFIER','LBRACE','RBRACE'])['accepted'])
    check('INT-01','All valid sample cases match expected labels',['CONFORMING','NONCONFORMING','INCOMPLETE','NONCONFORMING','INCOMPLETE'],lambda:[model.simulate(w)['classification'] for w in [['approve','purchase','pay','complete'],['approve','pay','complete'],['approve','purchase'],['approve','refund'],[]]])
    check('INT-02','Main parser and grammar lab agree on full source',True,lambda:grammar_lab(SOURCE)['cnf_cyk_accepts'] and grammar_lab(SOURCE)['pda']['accepted'])
    return records
