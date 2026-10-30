"""Run `python main.py --help`; runtime dependencies: Python standard library only."""
import argparse
import json
from pathlib import Path
from bpsl.compiler import compile_source, Diagnostic
from bpsl.labs import regex_lab, grammar_lab


def main():
    parser = argparse.ArgumentParser(description='BPSL compiler and conformance checker')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run', help='compile BPSL and simulate event symbols')
    run.add_argument('source', type=Path)
    run.add_argument('--events', default='', help='space-separated event identifiers; empty means no events')
    run.add_argument('--details', action='store_true', help='show tokens, parse tree, PDA and derivations')
    regex = sub.add_parser('regex', help='Thompson, subset, minimization, equivalence lab')
    regex.add_argument('pattern')
    regex.add_argument('--word', default='')
    gram = sub.add_parser('grammar', help='reference CFG transformations and PDA lab')
    gram.add_argument('source', type=Path)
    ui = sub.add_parser('ui', help='local browser interface')
    ui.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.command == 'ui':
        from bpsl.webapp import serve
        serve(args.port)
        return 0
    try:
        if args.command == 'regex':
            result = regex_lab(args.pattern, args.word)
        elif args.command == 'grammar':
            result = grammar_lab(args.source.read_text(encoding='utf-8'))
        else:
            artifact = compile_source(args.source.read_text(encoding='utf-8'))
            result = dict(process=artifact['parsed']['name'], automaton=artifact['model'].table(), findings=artifact['findings'],
                          events=args.events.split(), result=artifact['model'].simulate(args.events.split()))
            if args.details:
                result['tokens'] = artifact['tokens']
                result['parser'] = artifact['parsed']
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (Diagnostic, ValueError, OSError) as e:
        print(json.dumps(dict(error=str(e)), indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
