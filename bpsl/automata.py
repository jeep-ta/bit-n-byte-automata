"""Direct finite-automata algorithms; None denotes epsilon, never an event."""
from collections import deque
from dataclasses import dataclass


@dataclass
class DFA:
    states: set
    alphabet: set
    transitions: dict
    start: object
    accepts: set

    def reachable(self):
        seen, todo = {self.start}, [self.start]
        while todo:
            q = todo.pop()
            for a in self.alphabet:
                t = self.transitions.get((q, a))
                if t is not None and t not in seen:
                    seen.add(t)
                    todo.append(t)
        return seen

    def simulate(self, symbols):
        q, trace, prefix = self.start, [self.start], []
        for i, a in enumerate(symbols, 1):
            if (q, a) not in self.transitions:
                return dict(
                    classification='NONCONFORMING', final=q, trace=trace,
                    position=i, observed=a,
                    permitted=sorted(x for s, x in self.transitions if s == q),
                    valid_prefix=prefix,
                    reason=('unknown event' if a not in self.alphabet
                            else 'undefined transition'))
            q = self.transitions[q, a]
            trace.append(q)
            prefix.append(a)
        return dict(
            classification='CONFORMING' if q in self.accepts else 'INCOMPLETE',
            final=q, trace=trace, valid_prefix=prefix)

    def table(self):
        return dict(states=sorted(self.states, key=str), alphabet=sorted(self.alphabet), start=self.start,
                    accepts=sorted(self.accepts, key=str),
                    transitions=[dict(source=q, event=a, target=t) for (q, a), t in sorted(self.transitions.items(), key=lambda x: str(x[0]))])


@dataclass
class NFA:
    states: set
    alphabet: set
    transitions: dict
    start: int
    accepts: set
    steps: list

    def closure(self, states):
        seen, todo = set(states), list(states)
        while todo:
            q = todo.pop()
            for t in self.transitions.get((q, None), set()):
                if t not in seen:
                    seen.add(t)
                    todo.append(t)
        return frozenset(seen)

    def move(self, states, a):
        return set().union(*(self.transitions.get((q, a), set()) for q in states))

    def accepts_word(self, word):
        q = self.closure({self.start})
        for a in word:
            q = self.closure(self.move(q, a))
        return bool(q & self.accepts)

    def determinize(self):
        initial = self.closure({self.start})
        names, todo, trans, finals, log = {initial: 'D0'}, deque([initial]), {}, set(), []
        while todo:
            subset = todo.popleft()
            name = names[subset]
            if subset & self.accepts:
                finals.add(name)
            for a in sorted(self.alphabet):
                target = self.closure(self.move(subset, a))
                if target not in names:
                    names[target] = f'D{len(names)}'
                    todo.append(target)
                trans[name, a] = names[target]
                log.append(dict(source=name, symbol=a, move=sorted(self.move(subset, a)), closure=sorted(target), target=names[target]))
        dfa = DFA(set(names.values()), self.alphabet, trans, 'D0', finals)
        return dfa, dict(subsets={v: sorted(k) for k, v in names.items()}, steps=log)


def thompson(pattern):
    """Recursive regex parser: character literals, escapes, (), |, *, +, ?, and epsilon ε.

    Character classes are deliberately expanded by the caller. Dot is a literal.
    An empty expression denotes epsilon; empty alternatives are rejected.
    """
    pos, count, edges, steps, alphabet = 0, 0, {}, [], set()

    def state():
        nonlocal count
        q = count
        count += 1
        return q

    def edge(q, a, t):
        edges.setdefault((q, a), set()).add(t)
        if a is not None:
            alphabet.add(a)

    def atom():
        nonlocal pos
        if pos >= len(pattern):
            raise ValueError('Regex: missing operand at end')
        c = pattern[pos]
        pos += 1
        if c == '(':
            pair = expr()
            if pos >= len(pattern) or pattern[pos] != ')':
                raise ValueError('Regex: missing closing parenthesis')
            pos += 1
        else:
            if c in '|)*+?':
                raise ValueError(f'Regex: unexpected {c} at {pos}')
            if c == '\\':
                if pos >= len(pattern):
                    raise ValueError('Regex: trailing escape')
                c = pattern[pos]
                pos += 1
                symbol = c
            else:
                symbol = None if c == 'ε' else c
            pair = state(), state()
            edge(pair[0], symbol, pair[1])
            steps.append(dict(operation='literal' if symbol is not None else 'epsilon', symbol=symbol, fragment=pair))
        while pos < len(pattern) and pattern[pos] in '*+?':
            op = pattern[pos]
            pos += 1
            s, t = state(), state()
            edge(s, None, pair[0]); edge(pair[1], None, t)
            if op in '*?':
                edge(s, None, t)
            if op in '*+':
                edge(pair[1], None, pair[0])
            pair = s, t
            steps.append(dict(operation=op, fragment=pair))
        return pair

    def concat():
        pair = None
        while pos < len(pattern) and pattern[pos] not in '|)':
            nxt = atom()
            if pair is None:
                pair = nxt
            else:
                edge(pair[1], None, nxt[0])
                pair = pair[0], nxt[1]
                steps.append(dict(operation='concatenation', fragment=pair))
        if pair is None:
            raise ValueError('Regex: empty alternative or group; use ε')
        return pair

    def expr():
        nonlocal pos
        pair = concat()
        while pos < len(pattern) and pattern[pos] == '|':
            pos += 1
            right = concat()
            s, t = state(), state()
            edge(s, None, pair[0]); edge(s, None, right[0])
            edge(pair[1], None, t); edge(right[1], None, t)
            pair = s, t
            steps.append(dict(operation='alternation', fragment=pair))
        return pair

    if not pattern:
        s, t = state(), state()
        edge(s, None, t)
    else:
        s, t = expr()
        if pos != len(pattern):
            raise ValueError(f'Regex: unexpected closing parenthesis at {pos + 1}')
    return NFA(set(range(count)), alphabet, edges, s, {t}, steps)


def complete(dfa, alphabet=None):
    """Totalize with a fresh rejecting sink; preserve original domain names."""
    alphabet = set(dfa.alphabet if alphabet is None else alphabet)
    states, trans = set(dfa.states), dict(dfa.transitions)
    sink = '__sink__'
    while sink in states:
        sink += '_'
    missing = [(q, a) for q in states for a in alphabet if (q, a) not in trans]
    if missing:
        states.add(sink)
        for key in missing:
            trans[key] = sink
        for a in alphabet:
            trans[sink, a] = sink
    return DFA(states, alphabet, trans, dfa.start, set(dfa.accepts))


def minimize(dfa):
    d = complete(dfa)
    reachable = d.reachable()
    blocks = [g for g in [reachable & d.accepts, reachable - d.accepts] if g]
    history = [[sorted(g, key=str) for g in blocks]]
    while True:
        owner = {q: i for i, g in enumerate(blocks) for q in g}
        refined = []
        for group in blocks:
            buckets = {}
            for q in sorted(group, key=str):
                signature = tuple(owner[d.transitions[q, a]] for a in sorted(d.alphabet))
                buckets.setdefault(signature, set()).add(q)
            refined.extend(buckets.values())
        if len(refined) == len(blocks):
            break
        blocks = refined
        history.append([sorted(g, key=str) for g in blocks])
    names = {q: f'M{i}' for i, g in enumerate(blocks) for q in g}
    result = DFA(set(names.values()), d.alphabet,
                 {(names[q], a): names[d.transitions[q, a]] for q in reachable for a in d.alphabet},
                 names[d.start], {names[q] for q in reachable & d.accepts})
    return result, dict(partitions=history, classes={f'M{i}': sorted(g, key=str) for i, g in enumerate(blocks)},
                        removed_unreachable=sorted(dfa.states - dfa.reachable(), key=str))


def equivalent(left, right):
    """Complete decision procedure: reachable product BFS, shortest counterexample."""
    alphabet = left.alphabet | right.alphabet
    a, b = complete(left, alphabet), complete(right, alphabet)
    start = a.start, b.start
    todo, seen = deque([(start, [])]), {start}
    while todo:
        (p, q), word = todo.popleft()
        if (p in a.accepts) != (q in b.accepts):
            return dict(equivalent=False, counterexample=word, visited_pairs=len(seen))
        for symbol in sorted(alphabet):
            pair = a.transitions[p, symbol], b.transitions[q, symbol]
            if pair not in seen:
                seen.add(pair)
                todo.append((pair, word + [symbol]))
    return dict(equivalent=True, counterexample=None, visited_pairs=len(seen))
