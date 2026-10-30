"""BPSL CFG, predictive stack machine, derivations and grammar transformations.

Productions are tuples. Empty tuples denote epsilon. Terminals are token kinds.
"""
from dataclasses import dataclass
from itertools import product


@dataclass
class Grammar:
    start: str
    rules: dict

    @property
    def variables(self):
        return set(self.rules)

    @property
    def terminals(self):
        return {x for alternatives in self.rules.values() for rhs in alternatives for x in rhs} - self.variables

    def display(self):
        return '\n'.join(f'{v} -> ' + ' | '.join(' '.join(r) or 'epsilon' for r in sorted(rs)) for v, rs in self.rules.items())


BPSL = Grammar('process_spec', {
    'process_spec': {('PROCESS', 'IDENTIFIER', 'LBRACE', 'declaration_list', 'RBRACE')},
    'declaration_list': {('declaration', 'declaration_list'), ()},
    'declaration': {(x,) for x in ['state_decl', 'event_decl', 'start_decl', 'accept_decl', 'transition_decl']},
    'state_decl': {('STATE', 'IDENTIFIER', 'SEMICOLON')},
    'event_decl': {('EVENT', 'IDENTIFIER', 'SEMICOLON')},
    'start_decl': {('START', 'IDENTIFIER', 'SEMICOLON')},
    'accept_decl': {('ACCEPT', 'IDENTIFIER', 'SEMICOLON')},
    'transition_decl': {('TRANSITION', 'IDENTIFIER', 'ON', 'IDENTIFIER', 'TO', 'IDENTIFIER', 'SEMICOLON')},
})


def analysis(g):
    first = {v: set() for v in g.variables}
    def first_seq(seq):
        found = set()
        for x in seq:
            fs = first[x] if x in g.variables else {x}
            found |= fs - {''}
            if '' not in fs:
                return found
        return found | {''}
    changed = True
    while changed:
        changed = False
        for v, alternatives in g.rules.items():
            for rhs in alternatives:
                before = len(first[v])
                first[v] |= first_seq(rhs)
                changed |= len(first[v]) != before
    follow = {v: set() for v in g.variables}
    follow[g.start].add('EOF')
    changed = True
    while changed:
        changed = False
        for v, alternatives in g.rules.items():
            for rhs in alternatives:
                for i, x in enumerate(rhs):
                    if x in g.variables:
                        suffix = first_seq(rhs[i+1:])
                        before = len(follow[x])
                        follow[x] |= suffix - {''}
                        if '' in suffix:
                            follow[x] |= follow[v]
                        changed |= len(follow[x]) != before
    table, conflicts = {}, []
    for v, alternatives in g.rules.items():
        for rhs in sorted(alternatives):
            fs = first_seq(rhs)
            for a in (fs - {''}) | (follow[v] if '' in fs else set()):
                if (v, a) in table and table[v, a] != rhs:
                    conflicts.append((v, a))
                table[v, a] = rhs
    return first, follow, table, conflicts


def parse_stack(kinds, g=BPSL):
    """LL(1) CFG-to-PDA specialization. Stack top is left, empty-stack acceptance.

    q expands variables, matches/pops terminals; input must be fully consumed.
    Same production table builds the parse tree used by the main compiler.
    """
    _, _, table, conflicts = analysis(g)
    if conflicts:
        raise ValueError(f'Grammar is not LL(1): {conflicts}')
    words = list(kinds) + ['EOF']
    root = dict(symbol=g.start, children=[])
    stack, i, trace = [(g.start, root)], 0, []
    while stack:
        before = [s for s, _ in stack]
        x, node = stack.pop(0)
        look = words[i]
        if x in g.variables:
            rhs = table.get((x, look))
            if rhs is None:
                return dict(accepted=False, position=i, expected=sorted(a for v, a in table if v == x), observed=look, trace=trace, tree=root)
            children = [dict(symbol=s, children=[]) for s in rhs]
            node['children'] = children
            stack[0:0] = list(zip(rhs, children))
            action = f"expand {x} -> {' '.join(rhs) or 'epsilon'}"
        elif x == look:
            node['token_index'] = i
            i += 1
            action = f'match/pop {x}'
        else:
            return dict(accepted=False, position=i, expected=[x], observed=look, trace=trace, tree=root)
        trace.append(dict(state='q', input_position=i, lookahead=look, stack_before=before, stack_after=[s for s, _ in stack], action=action))
    accepted = i == len(kinds)
    return dict(accepted=accepted, position=i, expected=['EOF'], observed=words[i], trace=trace,
                acceptance='empty stack AND exhausted input', tree=root)


def derivation(tree, rightmost=False):
    """Expand nodes from the actual parse tree, retaining token categories."""
    frontier, forms = [tree], [[tree['symbol']]]
    while True:
        choices = [i for i, n in enumerate(frontier) if n['symbol'] in BPSL.variables]
        if not choices:
            return forms
        i = choices[-1] if rightmost else choices[0]
        frontier[i:i+1] = frontier[i]['children']
        forms.append([n['symbol'] for n in frontier])


def simplify(g):
    """Nullable -> epsilon removal -> unit closure -> productive/reachable pruning."""
    rules = {v: set(rs) for v, rs in g.rules.items()}
    # Fresh start preserves epsilon without placing start on any RHS.
    start = 'S0'
    while start in rules or start in g.terminals:
        start += '_'
    rules[start] = {(g.start,)}
    nullable = set()
    changed = True
    while changed:
        old = set(nullable)
        nullable |= {v for v, rs in rules.items() if any(all(x in nullable for x in r) for r in rs)}
        changed = old != nullable
    epsfree = {v: set() for v in rules}
    for v, rs in rules.items():
        for rhs in rs:
            variants = {()}
            for x in rhs:
                variants = {r + tail for r in variants for tail in ([(x,), ()] if x in nullable else [(x,)])}
            epsfree[v] |= {r for r in variants if r or v == start}
    logs = [('nullable', sorted(nullable)), ('epsilon elimination', Grammar(start, epsfree).display())]
    unitfree = {}
    for v in rules:
        closure, todo = {v}, [v]
        while todo:
            for r in epsfree[todo.pop()]:
                if len(r) == 1 and r[0] in rules and r[0] not in closure:
                    closure.add(r[0]); todo.append(r[0])
        unitfree[v] = {r for u in closure for r in epsfree[u] if not (len(r) == 1 and r[0] in rules)}
    logs.append(('unit elimination', Grammar(start, unitfree).display()))
    productive = set()
    while True:
        old = set(productive)
        productive |= {v for v, rs in unitfree.items() if any(all(x not in rules or x in productive for x in r) for r in rs)}
        if productive == old:
            break
    pruned = {v: {r for r in rs if all(x not in rules or x in productive for x in r)} for v, rs in unitfree.items() if v in productive}
    reachable, todo = {start}, [start]
    while todo:
        for rhs in pruned.get(todo.pop(), set()):
            for x in rhs:
                if x in pruned and x not in reachable:
                    reachable.add(x); todo.append(x)
    result = Grammar(start, {v: rs for v, rs in pruned.items() if v in reachable})
    result.rules.setdefault(start, set())
    logs += [('productive', sorted(productive)), ('reachable', sorted(reachable)), ('useless elimination', result.display())]
    return result, logs


def cnf(g):
    simple, log = simplify(g)
    rules = {v: set() for v in simple.rules}
    terminals = {}
    counter = 0
    def fresh():
        nonlocal counter
        while True:
            counter += 1
            name = f'N{counter}'
            if name not in rules and name not in g.terminals:
                rules[name] = set()
                return name
    for v, rs in simple.rules.items():
        for rhs in sorted(rs):
            rhs = list(rhs)
            if len(rhs) > 1:
                for i, x in enumerate(rhs):
                    if x not in simple.variables:
                        if x not in terminals:
                            terminals[x] = fresh()
                            rules[terminals[x]].add((x,))
                        rhs[i] = terminals[x]
            owner = v
            while len(rhs) > 2:
                nxt = fresh()
                rules[owner].add((rhs[0], nxt))
                owner, rhs = nxt, rhs[1:]
            rules[owner].add(tuple(rhs))
    result = Grammar(simple.start, rules)
    return result, log + [('CNF', result.display())]


def gnf(g):
    """Terminal-leading substitution for acyclic leading-variable dependencies.

    Covers the full reference BPSL grammar; explicitly refuses left-recursive
    dependency cycles rather than claiming a general CFG-to-GNF implementation.
    """
    simple, log = simplify(g)
    cache = {}
    def expand(v, active):
        if v in active:
            raise ValueError('GNF supports acyclic leading-variable dependencies only')
        if v in cache:
            return cache[v]
        result = set()
        for r in simple.rules[v]:
            if r and r[0] in simple.variables:
                result |= {p + r[1:] for p in expand(r[0], active | {v})}
            else:
                result.add(r)
        cache[v] = result
        return result
    rules = {v: set(expand(v, set())) for v in simple.rules}
    wrappers = {}
    for v in list(rules):
        transformed = set()
        for r in rules[v]:
            row = list(r)
            for i in range(1, len(row)):
                x = row[i]
                if x not in rules:
                    if x not in wrappers:
                        name = 'T_' + x
                        while name in rules or name in simple.terminals or name in wrappers.values():
                            name += '_'
                        wrappers[x] = name
                    row[i] = wrappers[x]
            transformed.add(tuple(row))
        rules[v] = transformed
    rules.update({v: {(x,)} for x, v in wrappers.items()})
    result = Grammar(simple.start, rules)
    return result, log + [('GNF (acyclic leading dependencies)', result.display())]


def cyk(g, words):
    """Membership check for a CNF grammar, independent of the LL(1) parser."""
    n = len(words)
    if n == 0:
        return () in g.rules[g.start]
    cells = {}
    for i, a in enumerate(words):
        cells[i, 1] = {v for v, rs in g.rules.items() if (a,) in rs}
    for size in range(2, n+1):
        for i in range(n-size+1):
            found = set()
            for k in range(1, size):
                pairs = set(product(cells[i, k], cells[i+k, size-k]))
                found |= {v for v, rs in g.rules.items() if rs & pairs}
            cells[i, size] = found
    return g.start in cells[0, n]
