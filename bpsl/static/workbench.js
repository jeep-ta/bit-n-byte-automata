(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const form = $('analysis-form'), source = $('source');
  const sample = JSON.parse($('sample-data').textContent);
  const report = JSON.parse($('report-data').textContent);
  let toastTimer;
  function toast(message) {
    $('toast').textContent = message;
    $('toast').hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, 3500);
  }
  function updateLines() {
    const count = source.value.split('\n').length;
    $('line-numbers').textContent = Array.from({length: count}, (_, i) => i + 1).join('\n');
    $('line-count').textContent = `${count} lines`;
    $('line-numbers').scrollTop = source.scrollTop;
  }
  function dirty() {
    $('stale-notice').hidden = false;
    $('export').disabled = true;
  }
  function showMode(mode) {
    $('process-inputs').hidden = mode !== 'process';
    $('regex-inputs').hidden = mode !== 'regex';
    $('grammar-inputs').hidden = mode !== 'grammar';
    $('source-panel').hidden = mode === 'regex';
    form.querySelector('.workspace-grid').style.gridTemplateColumns = mode === 'regex' ? 'minmax(0, 1fr)' : '';
    $('input-title').textContent = mode === 'regex' ? 'Language & test word' : mode === 'grammar' ? 'Explore the grammar' : 'Execution inputs';
    document.body.dataset.mode = mode;
  }
  showMode($('mode').value);
  updateLines();
  source.addEventListener('input', updateLines);
  source.addEventListener('scroll', () => { $('line-numbers').scrollTop = source.scrollTop; });
  source.addEventListener('keydown', event => {
    if (event.key === 'Tab' && !event.shiftKey) {
      event.preventDefault();
      source.setRangeText('    ', source.selectionStart, source.selectionEnd, 'end');
      updateLines(); dirty();
    }
  });
  form.addEventListener('input', dirty);
  document.querySelectorAll('[data-mode]').forEach(button => {
    if (button.tagName !== 'BUTTON') return;
    button.addEventListener('click', () => {
      const mode = button.dataset.mode;
      if ($('mode').value === mode) return;
      $('mode').value = mode;
      form.requestSubmit();
    });
  });
  $('load-sample').addEventListener('click', () => {
    source.value = sample; updateLines(); dirty();
    toast('Reference specification loaded. Run analysis when ready.');
  });
  document.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click', () => {
    const sequences = {conforming: 'approve purchase pay complete', violation: 'approve pay complete', incomplete: 'approve purchase'};
    source.value = sample;
    $('events').value = sequences[button.dataset.preset];
    updateLines(); dirty();
    toast(`${button.textContent.replace('↗', '').trim()} demo loaded. Run analysis to inspect it.`);
  }));
  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault(); form.requestSubmit();
    }
  });
  form.addEventListener('submit', () => {
    $('run-button').disabled = true;
    $('run-button').firstElementChild.textContent = 'Analyzing…';
    // Persist presentation preference for the next server-rendered response.
    try { sessionStorage.setItem('bnb-result-focus', 'yes'); } catch (_) { /* optional */ }
  });
  $('export').disabled = !report;
  $('export').addEventListener('click', () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify({team: "Bit N' Byte", mode: $('mode').value, source: source.value, events: $('events').value, pattern: $('pattern').value, word: $('word').value, analysis: report}, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = `bit-n-byte-${$('mode').value}-analysis.json`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('Analysis exported as JSON.');
  });
  function present(enabled) {
    document.body.classList.toggle('presentation', enabled);
    $('present').setAttribute('aria-pressed', String(enabled));
    $('present').querySelector('span').textContent = enabled ? 'Exit present' : 'Present';
  }
  $('present').addEventListener('click', () => {
    const enabled = !document.body.classList.contains('presentation');
    present(enabled);
    try { sessionStorage.setItem('bnb-present', String(enabled)); } catch (_) { /* optional */ }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      present(false);
      try { sessionStorage.setItem('bnb-present', 'false'); } catch (_) { /* optional */ }
    }
  });
  try {
    present(sessionStorage.getItem('bnb-present') === 'true');
    if (sessionStorage.getItem('bnb-result-focus') === 'yes') {
      sessionStorage.removeItem('bnb-result-focus');
      window.addEventListener('pageshow', () => {
        requestAnimationFrame(() => $('results').scrollIntoView({behavior: 'instant'}));
      }, {once: true});
    }
  } catch (_) { /* Storage can be unavailable in private browser contexts. */ }
})();
