/* Pure bounded model: host feedback changes display only; selection is an explicit user action. */
(function (root) {
  'use strict';
  root.HistoryModel = function () {
    let values = [], selected = -1;
    let settings = {SignalVariable: 'skill_demo_signal', Caption: 'Signal history', SampleLimit: 60,
                    TraceColor: '#64ddd0', ShowValues: true, Scale: 'auto'};
    function configure(params) {
      const old = settings.SignalVariable;
      for (const key of Object.keys(settings)) if (Object.prototype.hasOwnProperty.call(params, key)) settings[key] = params[key];
      const limit = Number(settings.SampleLimit);
      settings.SampleLimit = Number.isFinite(limit) ? Math.max(3, Math.min(120, Math.round(limit))) : 60;
      if (old !== settings.SignalVariable) { values = []; selected = -1; }
      if (values.length > settings.SampleLimit) { values = values.slice(-settings.SampleLimit); selected = -1; }
      return old !== settings.SignalVariable;
    }
    function update(variables) {
      const raw = variables[settings.SignalVariable];
      if (raw == null || typeof raw === 'boolean' || (typeof raw !== 'number' && typeof raw !== 'string') || (typeof raw === 'string' && !raw.trim())) return false;
      const value = Number(raw);
      if (!Number.isFinite(value) || (values.length && values[values.length - 1] === value)) return false;
      values.push(value);
      if (values.length > settings.SampleLimit) { values.shift(); selected = Math.max(-1, selected - 1); }
      return true;
    }
    function points() {
      if (!values.length) return [];
      let low = settings.Scale === 'percent' ? 0 : Math.min(...values);
      let high = settings.Scale === 'percent' ? 100 : Math.max(...values);
      const scale = Math.max(1, Math.abs(low), Math.abs(high));
      const minimum = low / scale, range = high / scale - minimum;
      return values.map((v, i) => [values.length === 1 ? 300 : 24 + i * 552 / (values.length - 1),
                                  216 - (range ? Math.max(0, Math.min(1, (v / scale - minimum) / range)) : 0.5) * 192]);
    }
    return {
      configure, update, points,
      get settings() { return {...settings}; },
      get values() { return values.slice(); },
      get selected() { return selected; },
      select(index) {
        if (!values.length || !Number.isFinite(index)) return null;
        selected = Math.max(0, Math.min(values.length - 1, Math.round(index)));
        return {value: values[selected], index: selected};
      }
    };
  };
})(window);
