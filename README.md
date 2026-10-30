# Bit N' Byte — BPSL Automata Workbench

A Formal Language and Automata-Based System for Business Process Specification,
Conformance Checking, and Violation Detection

Group: Mark Neil D. Oligo and Jeptha M. Osorio. Course: Automata and Compiler
Theories and Formal Languages, BS Computer Science - K36. Instructor: Mr. Maxil S. Urocay.

## Startup

Install Python 3.10 or newer. The application and tests use only the Python standard
library. No pip install, network connection, API key, or external service is required.
Clone this repository and open a terminal in its root directory:

```powershell
python --version
python main.py ui
```

Open http://127.0.0.1:8765 in a browser. The initial form loads the reference
procurement specification. Select an operation and click **Run analysis**.
Use Ctrl+C in the terminal to stop. If the port is occupied:

```powershell
python main.py ui --port 8770
```

Then open http://127.0.0.1:8770. The interface binds only to the local computer.
On systems where the Python command is `python3`, replace `python` accordingly.

## Bit N' Byte demonstration interface

The workbench includes a dark Bit N' Byte theme, a numbered source editor, a
process diagram highlighting executed transitions, state-by-state traces, and
expandable compiler evidence. A real reference analysis appears on first visit.

Use the Conforming, Violation, and Incomplete presets, then Run analysis. Presets
restore the procurement source. Switch tools from the navigation to explore the
regex and grammar/PDA labs. Ctrl+Enter (Cmd+Enter on macOS) runs the current tool.
Present hides the sidebar for a wider demonstration view; Escape exits that view.
Export results downloads a JSON report. Editing inputs marks results as outdated
and disables export until analysis is rerun. All assets work offline.

The demonstration preview uses http://127.0.0.1:8770 when 8765 is already occupied:

```powershell
python main.py ui --port 8770
```

## Console and tests

```powershell
python main.py run samples/procurement.bpsl --events "approve purchase pay complete"
python main.py run samples/procurement.bpsl --events "approve pay complete"
python main.py run samples/procurement.bpsl --events "approve purchase"
python main.py run samples/procurement.bpsl --events ""
python main.py run samples/procurement.bpsl --events "approve" --details
python main.py regex "(a|b)*abb" --word aabb
python main.py grammar samples/procurement.bpsl
python run_tests.py --output test_results
python -m unittest discover -v
```

`run_tests.py` records each scenario's expected and actual results and PASS/FAIL in
JSON and CSV. The unittest command wraps the same scenarios in **one test method
with subtests**; it does not mean 99 separately discovered test methods. The recorded
milestone run passed 99/99 scenarios. Rerun to obtain results for your environment.
CLI validation errors exit with code 2. Valid compilations exit 0 even when the
observed execution is nonconforming or incomplete; classification is in the JSON.

## Language and validation

The grammar is the proposal Appendix A grammar, represented in `bpsl/grammar.py`.
Keywords and identifiers are case-sensitive. Identifiers use the ASCII pattern
`[A-Za-z_][A-Za-z0-9_]*`. Reserved uppercase keywords take precedence. Identifiers
in state and event namespaces may share a spelling. Forward references are allowed
because structural validation follows complete parsing.

Exactly one PROCESS block, one START, at least one STATE, EVENT, and ACCEPT are
required. All references must resolve in the appropriate namespace. Duplicate state,
event, accept, and transition declarations are rejected, including identical repeated
transitions. Multiple START declarations are rejected. Each state/event pair has at
most one destination. Unreachable states and accepting states are findings; they do
not cause syntax rejection. A dead-end accepting state is a valid completion state.

Business events are **whole symbols**, e.g. `approve`, not character strings for the
source lexer. The CLI and UI split event sequences on whitespace. BPSL source token
`IDENTIFIER` is a category, not an execution event. Comments, quoted identifiers,
timers, concurrency and guards are outside this version's syntax.

For a process automaton, a missing transition gives NONCONFORMING at the first
invalid event (positions start at 1). A fully consumed sequence is CONFORMING only
if its final state is accepting; otherwise it is INCOMPLETE. No invalid-transition
position is invented for incomplete input. Unknown events have a distinct reason.
An empty sequence is accepted exactly when the start state is accepting.

## Algorithms and architecture

- `bpsl/automata.py`: direct regex parser, Thompson epsilon-NFA, closure, NFA
  simulation, subset construction, DFA simulation, partition refinement, complete
  product-automaton equivalence with shortest counterexample.
- `bpsl/compiler.py`: identifier recognizer actually constructed from regex through
  Thompson and subset construction; lexer, parse-tree integration, symbol checks,
  process automaton and structural findings.
- `bpsl/grammar.py`: reference CFG, FIRST/FOLLOW and LL(1) table, predictive stack
  PDA, parse tree, both derivations, epsilon/unit/useless-symbol elimination, CNF,
  scoped GNF, and independent CYK membership check.
- `bpsl/labs.py`: exposes formal intermediate steps. Regex lab is an educational
  view of the same conversion algorithms used by the identifier recognizer.
  Grammar transformations analyze the BPSL syntax language; they do not rewrite
  the process's business-event language. The main parser uses the original CFG.
- `bpsl/webapp.py` and `main.py`: browser/console inputs, intermediates and errors.

Regex lab supports literals, escapes, alternation `|`, implicit concatenation,
grouping `()`, `*`, `+`, `?`, epsilon `ε` and empty regex. Empty alternatives must
be written explicitly with epsilon. Dot is a literal; character-class brackets,
wildcards and anchors are not regex metasyntax here. The identifier pattern is
expanded into literal alternatives by the program. Python's `re` is not used.

Minimization totalizes missing transitions with a fresh rejecting sink, removes
unreachable states and refines accepting/nonaccepting partitions. The original
process automaton keeps semantic state names and first-violation diagnostics.
Minimized automata preserve accepted language, not necessarily early rejection
timing or business-state meaning.

GNF conversion fully covers the reference BPSL grammar and accepts grammars with
acyclic leading-variable dependencies after simplification. It explicitly refuses
left-recursive leading cycles; it is not a universal GNF converter. CNF preserves
epsilon only through a fresh start symbol. Grammar transformations can expand
substantially and are intended for small teaching examples. The PDA uses empty
stack **and exhausted input** as its acceptance condition. LL(1) conflict freedom
establishes unambiguity for this grammar, not for arbitrary user grammars.

## Evidence and remaining scope

The original course submission, kept separately from this source repository,
contains nine browser viewport screenshots, capture metadata, formal artifacts,
CLI runs, test records, a report, and a demonstration guide. Screenshot capture uses an
optional development-only Node/Playwright tool; neither is an application dependency.

The requirements inventory retains 32 groups. 26 completed groups / 32 = 81.25%
under disclosed equal weighting, a self-assessment not instructor approval.
The memo minimum is 70%; the proposal's cumulative targets are 50%, 75%, 100%.
TM/RAM, computability, full complexity analysis, polynomial reduction, performance
benchmarks, and final paper/video/defense remain pending Final-term work. No
performance results are claimed. The project is a small-input teaching prototype;
full intermediate traces and derivations can consume substantial memory.

## AI assistance and ownership

Codex generated the initial code, tests, samples and documentation during this
session, executed tests and captured evidence. No pre-existing member implementation
or historical contribution is claimed. The members must review and understand the
code and report before submission and reconcile this substantial AI assistance
with applicable instructor policy. Proposed ownership of remaining work is in the
report and is not a record of completed individual contributions.

No submission or external messaging was performed.
