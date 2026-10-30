"""Preliminary midterm compiler and DFA measurements; standard library only."""
import argparse
import csv
import json
import platform
import statistics
import time
import tracemalloc
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bpsl.compiler import compile_source, identifier_automata


def chain(n):
    return '\n'.join(['PROCESS Chain {']+[f'STATE Q{i};' for i in range(n)]+
        ['EVENT next;', 'START Q0;',f'ACCEPT Q{n-1};']+
        [f'TRANSITION Q{i} ON next TO Q{i+1};' for i in range(n-1)]+['}'])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('benchmark_results'))
    parser.add_argument('--trials',type=int,default=7)
    args=parser.parse_args()
    if args.trials<3:
        parser.error('At least three trials required')
    args.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    def measure(component,size,operation,**dimensions):
        operation()  # warm-up, not included in the measurements
        times=[]
        for _ in range(args.trials):
            start=time.perf_counter_ns()
            result=operation()
            times.append((time.perf_counter_ns()-start)/1e6)
            del result
        tracemalloc.start()
        operation()
        _, peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rows.append(dict(component=component,size=size,**dimensions,trials=args.trials,
                         times_ms=times,median_ms=statistics.median(times),
                         minimum_ms=min(times),maximum_ms=max(times),peak_python_kib=peak/1024))
    identifier_automata()  # isolate compilation from first-use recognizer construction
    for n in [5,10,25,50,100]:
        source=chain(n)
        artifact=compile_source(source)
        measure('compile',n,lambda s=source:compile_source(s),source_characters=len(source),
                tokens=len(artifact['tokens'])-1,pda_steps=len(artifact['parsed']['pda']['trace']),
                max_stack=max(len(t['stack_before']) for t in artifact['parsed']['pda']['trace']))
    loop=compile_source('PROCESS Loop { STATE S; EVENT a; START S; ACCEPT S; TRANSITION S ON a TO S; }')['model']
    for n in [10,100,1000,10000,100000]:
        words=['a']*n
        measure('dfa_simulation',n,lambda w=words:loop.simulate(w),states=1,transitions=1)
    data=dict(date=datetime.now(timezone(timedelta(hours=8))).isoformat(),python=platform.python_version(),
              platform=platform.platform(),processor=platform.processor(),trials=args.trials,
              method='perf_counter_ns; one untimed warm-up; seven trials by default; separate tracemalloc peak run; no outliers removed; warm identifier cache',
              limitations='Preliminary midterm measurements on one machine; synthetic inputs; Python traced allocations are not process RSS; compilation retains full evidence',results=rows)
    (args.output/'results.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    keys=sorted(set().union(*(r.keys() for r in rows))-{'times_ms'})
    with (args.output/'results.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    for row in rows:
        print(f"{row['component']} n={row['size']}: {row['median_ms']:.4f} ms; {row['peak_python_kib']:.1f} KiB")


if __name__=='__main__':
    main()
