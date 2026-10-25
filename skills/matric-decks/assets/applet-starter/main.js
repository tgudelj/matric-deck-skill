(function () {
  'use strict';
  const model = new window.HistoryModel();
  const el = id => document.getElementById(id);
  const chart = el('chart');
  function render() {
    const settings = model.settings, values = model.values, points = model.points();
    el('caption').textContent = String(settings.Caption ?? 'Signal history');
    if (CSS.supports('color', String(settings.TraceColor))) document.documentElement.style.setProperty('--trace', settings.TraceColor);
    el('latest').textContent = values.length ? (settings.ShowValues ? String(values[values.length - 1]) : 'Receiving values') : 'Waiting for a value';
    el('trace').setAttribute('points', points.map(p => p.join(',')).join(' '));
    el('count').textContent = values.length + (values.length === 1 ? ' sample' : ' samples');
    const latest = points[points.length - 1];
    el('endpoint').toggleAttribute('hidden', !latest);
    if (latest) { el('endpoint').setAttribute('cx', latest[0]); el('endpoint').setAttribute('cy', latest[1]); }
    const point = points[model.selected];
    el('marker').toggleAttribute('hidden', !point);
    if (point) { el('marker').setAttribute('cx', point[0]); el('marker').setAttribute('cy', point[1]); }
    el('selection').textContent = point ? (settings.ShowValues ? 'Selected: ' + values[model.selected] : 'Sample selected') : 'Tap a sample to inspect it';
  }
  const bridge = new window.MatricApplet({
    params(params) { const changed = model.configure(params); render(); if (changed) bridge.requestVariables(model.settings.SignalVariable); },
    variables(variables) { if (model.update(variables)) render(); },
    resize() { render(); } // Responsive CSS follows the iframe; no fixed-canvas zoom.
  });
  function select(index) {
    const data = model.select(index);
    if (!data) return;
    render();
    bridge.emit('select-sample', data);
    // Supports prompt release if the user later binds a held input action on a compatible host.
    bridge.release('select-sample');
  }
  chart.addEventListener('pointerup', event => {
    if (event.button != null && event.button !== 0) return;
    const rect = chart.getBoundingClientRect();
    const fraction = ((event.clientX - rect.left) / Math.max(rect.width, 1) * 600 - 24) / 552;
    select(fraction * (model.values.length - 1));
  });
  chart.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      model.select((model.selected < 0 ? model.values.length - 1 : model.selected) + (event.key === 'ArrowLeft' ? -1 : 1));
      render();
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault(); select(model.selected < 0 ? model.values.length - 1 : model.selected);
    }
  });
  function cancel() { bridge.release('select-sample'); }
  window.addEventListener('blur', cancel);
  chart.addEventListener('pointercancel', cancel);
  window.addEventListener('pagehide', () => { cancel(); bridge.dispose(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) cancel(); });
  render();
  bridge.requestVariables(model.settings.SignalVariable);
})();
