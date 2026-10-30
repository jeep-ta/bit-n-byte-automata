"""Inspectable educational artifacts derived from the production grammar/models."""
from .automata import thompson, minimize, equivalent
from .grammar import BPSL, analysis, simplify, cnf, gnf, cyk, derivation, parse_stack
from .compiler import identifier_automata, lex, parse


def regex_lab(pattern='(a|b)*abb', word='aabb'):
    nfa = thompson(pattern)
    dfa, subset = nfa.determinize()
    small, refinement = minimize(dfa)
    return dict(pattern=pattern, input=word,
                nfa=dict(states=sorted(nfa.states), start=nfa.start, accepts=sorted(nfa.accepts),
                         transitions=[dict(source=q, symbol=a if a is not None else 'epsilon', target=sorted(ts)) for (q, a), ts in nfa.transitions.items()],
                         thompson_steps=nfa.steps, initial_closure=sorted(nfa.closure({nfa.start}))),
                dfa=dfa.table(), subset_construction=subset, minimization=refinement,
                minimized=small.table(), nfa_accepts=nfa.accepts_word(word),
                simulation=dfa.simulate(word), minimized_simulation=small.simulate(word),
                complete_equivalence=equivalent(dfa, small))


def grammar_lab(source):
    tokens = lex(source)
    kinds = [t.kind for t in tokens[:-1]]
    pda = parse_stack(kinds)
    simple, steps = simplify(BPSL)
    normal, cnfsteps = cnf(BPSL)
    greibach, gnfsteps = gnf(BPSL)
    first, follow, table, conflicts = analysis(BPSL)
    result = dict(grammar=BPSL.display(), first={k: sorted(v) for k, v in first.items()},
                  follow={k: sorted(v) for k, v in follow.items()},
                  ll1_conflicts=conflicts,
                  ambiguity_analysis='No LL(1) table conflicts: this grammar is unambiguous. This is not a general ambiguity decider.',
                  simplification_steps=steps, simplified=simple.display(), cnf=normal.display(), cnf_steps=cnfsteps,
                  gnf=greibach.display(), gnf_steps=gnfsteps,
                  gnf_scope='Complete reference BPSL grammar; other grammars must have acyclic leading-variable dependencies.',
                  cnf_cyk_accepts=cyk(normal, kinds), pda=pda,
                  input_token_categories=kinds)
    if pda['accepted']:
        result.update(leftmost=derivation(pda['tree']), rightmost=derivation(pda['tree'], True), tree=pda['tree'])
    return result
