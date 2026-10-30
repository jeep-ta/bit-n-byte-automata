"""Retained regression cases and the additional Midterm formal-language checks."""
from bpsl.automata import thompson
from bpsl.grammar import Grammar, analysis, parse_stack, cnf, cyk
from bpsl.labs import regex_lab
from .scenarios import run_cases


def run_midterm_cases():
    records = run_cases()

    def check(id, scenario, input_definition, expected, operation):
        try:
            actual = operation()
        except Exception as error:
            actual = f'UNEXPECTED {type(error).__name__}: {error}'
        records.append(dict(id=id, scenario=scenario, expected=expected, actual=actual,
                            status='PASS' if actual == expected else 'FAIL',
                            input_definition=input_definition))

    ambiguous = Grammar('S', {'S': {('S', 'S'), ('a',)}})
    check('CFG-17', 'Ambiguous fixture conflicts', 'S -> S S | a; aaa', True,
          lambda: bool(analysis(ambiguous)[3]))

    def refuses():
        try:
            parse_stack(list('aaa'), ambiguous)
        except ValueError:
            return 'NOT LL1'
        return 'UNEXPECTED ACCEPT'

    check('CFG-18', 'Parser refuses a conflicting table', 'S -> S S | a; aaa',
          'NOT LL1', refuses)
    balanced = Grammar('S', {'S': {('a', 'S', 'b'), ()}})
    for id, word, expected in [('MT-01', 'aabb', True), ('MT-02', 'aab', False),
                               ('MT-03', '', True)]:
        check(id, 'Balanced language stack membership', word, expected,
              lambda w=word: parse_stack(list(w), balanced)['accepted'])
    normal = cnf(balanced)[0]
    check('MT-04', 'Independent balanced CNF membership', 'aabb', True,
          lambda: cyk(normal, list('aabb')))
    check('MT-05', 'Independent balanced CNF rejection', 'aab', False,
          lambda: cyk(normal, list('aab')))

    def deep():
        result = parse_stack(list('a' * 40 + 'b' * 40), balanced)
        return [result['accepted'], max(len(x['stack_before']) for x in result['trace'])]

    check('MT-06', 'Deeper stack with equal blocks', 'a^40 b^40', [True, 42], deep)
    small = regex_lab()['minimized']
    check('MT-07', 'Measured minimized model size', '(a|b)*abb', [4, 8],
          lambda: [len(small['states']), len(small['transitions'])])
    dfa = thompson('(a|b)*abb').determinize()[0]
    witnesses = [('', 'a', 'bb'), ('', 'ab', 'b'), ('', 'abb', ''),
                 ('a', 'ab', 'b'), ('a', 'abb', ''), ('ab', 'abb', '')]
    check('MT-08', 'All six Myhill Nerode distinguishing suffixes', witnesses, True,
          lambda: all((dfa.simulate(x + z)['classification'] == 'CONFORMING') !=
                      (dfa.simulate(y + z)['classification'] == 'CONFORMING')
                      for x, y, z in witnesses))
    return records
