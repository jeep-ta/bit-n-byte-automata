"""Run actual scenarios and persist expected/actual/status without external libraries."""
import argparse
import csv
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from tests.midterm_scenarios import run_midterm_cases


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('test_results'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    rows=run_midterm_cases()
    from datetime import timedelta
    tested = datetime.now(timezone(timedelta(hours=8))).isoformat()
    for row in rows:
        row.update(requirement=row['id'].split('-')[0], component=row['id'].split('-')[0],
                   formal_model='BPSL grammar / finite automata / predictive stack',
                   input=row.get('input',row.get('input_definition','See tests/scenarios.py: '+row['id']+'; '+row['scenario'])),
                   tester='Automated execution by Codex; no member review asserted',date_tested=tested,
                   corrective_action='None required in this run' if row['status']=='PASS' else 'Investigate mismatch')
    passed=sum(r['status']=='PASS' for r in rows)
    summary=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
                 platform=platform.platform(),scenarios=len(rows),passed=passed,failed=len(rows)-passed,
                 note='Scenario count, not unittest method count. Finite tests do not prove general correctness.',results=rows)
    (args.output/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    with (args.output/'results.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=True) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    for r in rows:
        print(f"{r['status']} {r['id']} {r['scenario']}".encode('ascii', 'backslashreplace').decode())
        if r['status']=='FAIL':
            print(f"  expected={r['expected']!r}; actual={r['actual']!r}")
    print(f'{passed}/{len(rows)} scenarios passed; {len(rows)-passed} failed.')
    return int(passed!=len(rows))


if __name__=='__main__':
    raise SystemExit(main())
