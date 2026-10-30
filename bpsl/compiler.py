"""Positioned lexer, grammar parser, structural validation and process compiler."""
from dataclasses import dataclass, asdict
from functools import lru_cache
from string import ascii_letters, digits
from .automata import thompson, DFA
from .grammar import BPSL, parse_stack, derivation

KEYWORDS = {'PROCESS', 'STATE', 'EVENT', 'START', 'ACCEPT', 'TRANSITION', 'ON', 'TO'}
DELIMITERS = {'{': 'LBRACE', '}': 'RBRACE', ';': 'SEMICOLON'}


class Diagnostic(ValueError):
    def __init__(self, stage, message, line=1, column=1):
        self.stage, self.message, self.line, self.column = stage, message, line, column
        super().__init__(f'{stage} {line}:{column}: {message}')


@dataclass
class Token:
    kind: str
    lexeme: str
    line: int
    column: int


@lru_cache(maxsize=1)
def identifier_automata():
    """Actual lexer recognizer is generated through Thompson + subset construction."""
    head = '|'.join(ascii_letters + '_')
    tail = '|'.join(ascii_letters + digits + '_')
    pattern = f'({head})({tail})*'
    nfa = thompson(pattern)
    dfa, log = nfa.determinize()
    return pattern, nfa, dfa, log


def lex(source):
    dfa = identifier_automata()[2]
    tokens, i, line, column = [], 0, 1, 1
    while i < len(source):
        c = source[i]
        if c in ' \t\r\n':
            line, column = (line + 1, 1) if c == '\n' else (line, column + 1)
            i += 1
            continue
        if c in DELIMITERS:
            tokens.append(Token(DELIMITERS[c], c, line, column))
            i += 1; column += 1
            continue
        # Maximal alphanumeric fragment; initial digits cannot be silently split.
        j = i
        while j < len(source) and source[j] in ascii_letters + digits + '_':
            j += 1
        word = source[i:j]
        if not word or dfa.simulate(word)['classification'] != 'CONFORMING':
            raise Diagnostic('LEXICAL', f'invalid fragment {word or c!r}', line, column)
        tokens.append(Token(word if word in KEYWORDS else 'IDENTIFIER', word, line, column))
        column += j - i; i = j
    tokens.append(Token('EOF', '', line, column))
    return tokens


def parse(tokens):
    result = parse_stack([t.kind for t in tokens[:-1]])
    if not result['accepted']:
        t = tokens[result['position']]
        raise Diagnostic('SYNTAX', f"expected {' or '.join(result['expected'])}; observed {t.kind} {t.lexeme!r}", t.line, t.column)
    declarations, i = [], 3
    while tokens[i].kind != 'RBRACE':
        t = tokens[i]
        size = 7 if t.kind == 'TRANSITION' else 3
        args = [tokens[j].lexeme for j in ([i+1, i+3, i+5] if size == 7 else [i+1])]
        declarations.append(dict(kind=t.kind, args=args, line=t.line, column=t.column))
        i += size
    return dict(name=tokens[1].lexeme, declarations=declarations, tree=result['tree'], pda=result,
                leftmost=derivation(result['tree']), rightmost=derivation(result['tree'], True))


def validate(parsed):
    states, events, starts, accepts, transitions = set(), set(), [], set(), {}
    errors = []
    def error(d, message):
        errors.append(f"{d['line']}:{d['column']}: {message}")
    for d in parsed['declarations']:
        kind, args = d['kind'], d['args']
        if kind in ('STATE', 'EVENT'):
            target = states if kind == 'STATE' else events
            if args[0] in target:
                error(d, f'duplicate {kind} {args[0]}')
            target.add(args[0])
        elif kind == 'START':
            starts.append(args[0])
        elif kind == 'ACCEPT':
            if args[0] in accepts:
                error(d, f'duplicate ACCEPT {args[0]}')
            accepts.add(args[0])
    if len(starts) != 1:
        errors.append('exactly one START required')
    if not accepts:
        errors.append('at least one ACCEPT required')
    if not states:
        errors.append('at least one STATE required')
    if not events:
        errors.append('at least one EVENT required')
    for d in parsed['declarations']:
        kind, args = d['kind'], d['args']
        refs = args[:1] if kind in ('START', 'ACCEPT') else [args[0], args[2]] if kind == 'TRANSITION' else []
        for q in refs:
            if q not in states:
                error(d, f'undeclared state {q}')
        if kind == 'TRANSITION':
            q, a, t = args
            if a not in events:
                error(d, f'undeclared event {a}')
            if (q, a) in transitions:
                error(d, f"{'conflicting' if transitions[q, a] != t else 'duplicate'} transition {q} ON {a}")
            transitions[q, a] = t
    if errors:
        raise Diagnostic('STRUCTURAL', '; '.join(errors))
    return DFA(states, events, transitions, starts[0], accepts)


def compile_source(source):
    tokens = lex(source)
    parsed = parse(tokens)
    model = validate(parsed)
    reachable = model.reachable()
    findings = dict(reachable=sorted(reachable), unreachable=sorted(model.states - reachable),
                    unreachable_accepts=sorted(model.accepts - reachable),
                    dead_ends=sorted(q for q in model.states if not any(s == q for s, _ in model.transitions)))
    return dict(tokens=[asdict(t) for t in tokens], parsed=parsed, model=model, findings=findings)
