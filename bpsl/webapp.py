"""Bit N' Byte's local workbench, backed by the same algorithms as the CLI."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from pathlib import Path
from html import escape
import json
from .compiler import compile_source, Diagnostic
from .labs import regex_lab, grammar_lab

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT.parent / 'samples' / 'procurement.bpsl'


def dump(value):
    return '<pre>' + escape(json.dumps(value, indent=2, ensure_ascii=False)) + '</pre>'


def details(title, value):
    return '<details><summary>' + escape(title) + '<span>Inspect +</span></summary>' + dump(value) + '</details>'


def metric(value, label):
    return '<div class="metric"><strong>' + escape(str(value)) + '</strong><span>' + escape(label) + '</span></div>'


def graph(model, result):
    """A scrollable SVG with full semantic state labels and all declared edges."""
    # Keep the layout stable across runs, ordering reachable states from start.
    states = [model.start]
    for state in states:
        for (origin, _), target in model.transitions.items():
            if origin == state and target not in states:
                states.append(target)
    states.extend(sorted(model.states - set(states)))
    width = max(650, len(states) * 170 + 60)
    positions = {q: 105 + i * 170 for i, q in enumerate(states)}
    traversed = set(zip(result['trace'], result['valid_prefix'], result['trace'][1:]))
    svg = f'<svg viewBox="0 0 {width} 290" role="img" aria-label="Process automaton. Double circles indicate accepting states."><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>'
    svg += f'<path class="edge" d="M 25 150 H {positions[model.start]-37}" marker-end="url(#arrow)"/>'
    for i, ((q, event), target) in enumerate(model.transitions.items()):
        x, end = positions[q], positions[target]
        active = ' active' if (q, event, target) in traversed else ''
        if q == target:
            path = f'M {x-20} 122 C {x-80} 35 {x+80} 35 {x+20} 122'
            tx, ty = x, 60
        elif end == x + 170:
            path = f'M {x+35} 150 H {end-38}'
            tx, ty = (x+end)/2, 134
        else:
            height = 42 + (i % 3) * 22
            path = f'M {x} 115 Q {(x+end)/2} {height} {end} 115'
            tx, ty = (x+end)/2, (height+115)/2-10
        svg += f'<path class="edge{active}" d="{path}" marker-end="url(#arrow)"/><text class="edge-label{active}" x="{tx}" y="{ty}">{escape(event)}</text>'
    for q, x in positions.items():
        cls = 'node visited' if q in result['trace'] else 'node'
        if q == result['final']:
            cls += ' current'
        svg += f'<g class="{cls}"><circle cx="{x}" cy="150" r="32"/>'
        if q in model.accepts:
            svg += f'<circle cx="{x}" cy="150" r="26"/>'
        svg += f'<text x="{x}" y="155">{states.index(q):02d}</text></g><text class="state-label" x="{x}" y="211">{escape(q)}</text>'
        if q == model.start or q in model.accepts:
            svg += f'<text class="state-kind" x="{x}" y="233">{"START" if q == model.start else "ACCEPT"}</text>'
    return '<div class="graph-scroll">' + svg + '</svg></div>'


def process_output(source, events):
    artifact = compile_source(source)
    model = artifact['model']
    result = model.simulate(events.split())
    status = result['classification']
    tone = {'CONFORMING': 'success', 'NONCONFORMING': 'danger', 'INCOMPLETE': 'warning'}[status]
    title, description = {
        'CONFORMING': ('Every step checks out.', 'All events follow the process and reach an accepting state.'),
        'NONCONFORMING': ('A transition needs attention.', 'The sequence contains an event that the current state does not permit.'),
        'INCOMPLETE': ('Valid so far. More to go.', 'The sequence follows the process, but has not reached an accepting state.')
    }[status]
    output = f'<section class="result-banner {tone}" role="status"><span class="result-icon">{"✓" if tone == "success" else "!"}</span><div><span class="eyebrow">{status}</span><h2>{title}</h2><p>{description}</p></div><span class="result-tag">ANALYSIS COMPLETE</span></section>'
    output += '<div class="metrics">' + metric(len(model.states), 'Declared states') + metric(len(model.transitions), 'Transitions') + metric(len(result['valid_prefix']), 'Events consumed') + metric(result['final'], 'Last valid state') + '</div>'
    if 'position' in result:
        output += '<div class="violation"><b>Stopped at event ' + str(result['position']) + ' · ' + escape(result['observed']) + '</b><p>From ' + escape(result['final']) + ', permitted next events: <code>' + escape(', '.join(result['permitted']) or 'none') + '</code>. Reason: ' + escape(result['reason']) + '.</p></div>'
    output += '<section class="panel"><div class="panel-heading"><div><span class="eyebrow">THE BIG PICTURE</span><h2>Process automaton</h2></div><span class="legend"><i></i> Executed path <span>◎ Accepting state</span></span></div>' + graph(model, result) + '</section>'
    output += '<section class="panel"><div class="panel-heading"><div><span class="eyebrow">STEP BY STEP</span><h2>Execution trace</h2></div><span class="subtle">' + str(len(result['trace'])) + ' states visited</span></div><ol class="trace">'
    for i, state in enumerate(result['trace']):
        output += '<li><span class="trace-index">' + f'{i:02d}' + '</span><span class="trace-event">' + escape('Start' if i == 0 else result['valid_prefix'][i-1]) + '</span><strong>' + escape(state) + '</strong></li>'
    output += '</ol><p class="fine-print">Classification describes the declared control flow; it does not establish real-world misconduct.</p></section>'
    rows = ''.join('<tr>' + ''.join('<td>' + escape(x) + '</td>' for x in (q, event, target)) + '</tr>' for (q, event), target in model.transitions.items())
    output += '<section class="panel evidence"><div class="panel-heading"><div><span class="eyebrow">UNDER THE HOOD</span><h2>Compiler evidence</h2></div><span class="subtle">Explore the formal steps</span></div><details><summary>Transition table<span>Inspect +</span></summary><div class="table-scroll"><table><thead><tr><th>Source state</th><th>Event</th><th>Target state</th></tr></thead><tbody>' + rows + '</tbody></table></div></details>'
    for title, data in [('Structural analysis', artifact['findings']), ('Source tokens', artifact['tokens']), ('Parse tree', artifact['parsed']['tree']), ('Leftmost derivation', artifact['parsed']['leftmost']), ('Rightmost derivation', artifact['parsed']['rightmost']), ('PDA stack trace', artifact['parsed']['pda']), ('Structured conformance result', result)]:
        output += details(title, data)
    return output + '</section>', dict(process=artifact['parsed']['name'], automaton=model.table(), result=result, findings=artifact['findings'])


def lab_output(mode, source, pattern, word):
    data = regex_lab(pattern, word) if mode == 'regex' else grammar_lab(source)
    if mode == 'regex':
        accepted = data['nfa_accepts']
        output = '<section class="result-banner ' + ('success' if accepted else 'warning') + '"><span class="result-icon">' + ('✓' if accepted else '!') + '</span><div><span class="eyebrow">REGEX AUTOMATA LAB</span><h2>' + ('A match, through every machine.' if accepted else 'The word is not in this language.') + '</h2><p>Thompson ε-NFA → subset DFA → minimized DFA</p></div></section>'
        output += '<div class="metrics">' + metric(len(data['nfa']['states']), 'ε-NFA states') + metric(len(data['dfa']['states']), 'DFA states') + metric(len(data['minimized']['states']), 'Minimized states') + metric('Yes' if data['complete_equivalence']['equivalent'] else 'No', 'Language equivalence') + '</div>'
        output += '<section class="panel"><span class="eyebrow">LANGUAGE EXPLORER</span><h2>From expression to execution</h2><div class="lab-expression"><code>' + escape(pattern or 'ε') + '</code><span>tested against</span><code>' + escape(word or 'ε') + '</code></div><p class="subtle">DFA trace · ' + escape(' → '.join(data['simulation']['trace'])) + '</p></section>'
    else:
        accepted = data['pda']['accepted']
        output = '<section class="result-banner ' + ('success' if accepted else 'danger') + '"><span class="result-icon">' + ('✓' if accepted else '!') + '</span><div><span class="eyebrow">GRAMMAR & PDA LAB</span><h2>' + ('The grammar comes together.' if accepted else 'The grammar rejected this source.') + '</h2><p>Inspect predictive parsing, transformations, and independent CYK membership.</p></div></section>'
        output += '<div class="metrics">' + metric(len(data['ll1_conflicts']), 'LL(1) conflicts') + metric('Accepted' if accepted else 'Rejected', 'PDA result') + metric('Accepted' if data['cnf_cyk_accepts'] else 'Rejected', 'CNF / CYK result') + metric(len(data['input_token_categories']), 'Input tokens') + '</div>'
        output += '<section class="panel"><span class="eyebrow">REFERENCE LANGUAGE</span><h2>BPSL grammar</h2><pre>' + escape(data['grammar']) + '</pre><p class="subtle">' + escape(data['ambiguity_analysis']) + '</p><p class="fine-print">GNF scope: ' + escape(data['gnf_scope']) + '</p></section>'
    output += '<section class="panel evidence"><div class="panel-heading"><div><span class="eyebrow">UNDER THE HOOD</span><h2>Formal artifacts</h2></div></div>'
    output += ''.join(details(k.replace('_', ' ').capitalize(), value) for k, value in data.items())
    return output + '</section>', data


def page(values=None):
    v = values or {}
    source = v.get('source', SAMPLE.read_text(encoding='utf-8'))
    events = v.get('events', 'approve purchase pay complete')
    mode = v.get('mode', 'process')
    if mode not in {'process', 'regex', 'grammar'}:
        mode = 'process'
    pattern, word = v.get('pattern', '(a|b)*abb'), v.get('word', 'aabb')
    report = None
    try:
        # Show a real, computed reference result on first visit.
        output, report = process_output(source, events) if mode == 'process' else lab_output(mode, source, pattern, word)
    except (Diagnostic, ValueError) as error:
        output = '<section class="result-banner danger" role="alert"><span class="result-icon">!</span><div><span class="eyebrow">INPUT ERROR</span><h2>Let’s check the specification.</h2><p>' + escape(str(error)) + '</p></div></section><section class="panel"><h2>Ready when you are.</h2><p class="subtle">Correct the input and run analysis again. Invalid source produces no process automaton or conformance result.</p></section>'
    labels = {'process': 'Process checker', 'regex': 'Regex lab', 'grammar': 'Grammar & PDA'}
    nav = ''.join('<button type="button" class="nav-item ' + ('selected' if key == mode else '') + '" data-mode="' + key + '"' + (' aria-current="page"' if key == mode else '') + '><span class="nav-icon">' + icon + '</span>' + label + '<span class="nav-number">' + number + '</span></button>' for key, label, icon, number in [('process', 'Process checker', '⌘', '01'), ('regex', 'Regex lab', '.*', '02'), ('grammar', 'Grammar & PDA', '{ }', '03')])
    template = (ROOT / 'static' / 'index.html').read_text(encoding='utf-8')
    replacements = {'NAV': nav, 'MODE': mode, 'LABEL': labels[mode], 'SOURCE': escape(source), 'EVENTS': escape(events, quote=True), 'PATTERN': escape(pattern, quote=True), 'WORD': escape(word, quote=True), 'OUTPUT': output, 'REPORT': json.dumps(report, ensure_ascii=True).replace('<', '\\u003c'), 'SAMPLE': json.dumps(SAMPLE.read_text(encoding='utf-8')).replace('<', '\\u003c')}
    import re
    return re.sub(r'@@([A-Z]+)@@', lambda match: replacements[match[1]], template)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        assets = {'/assets/workbench.css': ('workbench.css', 'text/css'), '/assets/workbench.js': ('workbench.js', 'text/javascript'), '/favicon.svg': ('favicon.svg', 'image/svg+xml'), '/assets/bit-n-byte-logo.png': ('bit-n-byte-logo.png', 'image/png')}
        if path in assets:
            filename, mime = assets[path]
            self.respond((ROOT / 'static' / filename).read_bytes(), mime)
        elif path == '/':
            self.respond(page())
        else:
            self.send_error(404)

    def do_POST(self):
        if urlsplit(self.path).path != '/':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 1000000:
                self.send_error(413)
                return
            values = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode(), keep_blank_values=True).items()}
        except (ValueError, UnicodeError):
            self.send_error(400)
            return
        self.respond(page(values))

    def respond(self, body, mime='text/html'):
        raw = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', mime if mime.startswith('image/') else mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve(port=8765):
    print(f"Bit N' Byte Workbench running at http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
