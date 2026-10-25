/* Original minimal MATRIC iframe bridge; no external SDK or network dependency. */
(function (root) {
  'use strict';
  root.MatricApplet = function (callbacks) {
    const id = root.location.hash.slice(1);
    const parent = root.parent;
    let targetOrigin = '*';
    const object = value => value && typeof value === 'object' && !Array.isArray(value);
    function emit(name, data) {
      if (!id || parent === root || typeof name !== 'string' || !name) return;
      parent.postMessage({messageId: 'cce-' + id, payload: {EventName: name, Data: data}}, targetOrigin);
    }
    function receive(event) {
      if (event.source !== parent || !object(event.data)) return;
      if (event.origin && event.origin !== 'null') targetOrigin = event.origin;
      const message = event.data;
      if (!object(message.payload)) return;
      if (message.messageId === 'PARAMSUPDATE') callbacks.params?.(message.payload);
      else if (message.messageId === 'VARIABLESUPDATE') callbacks.variables?.(message.payload);
      else if (message.messageId === 'RESIZE') callbacks.resize?.(message.payload);
    }
    root.addEventListener('message', receive);
    return {
      emit,
      requestVariables(name) { emit('reqvariables', name ? {variablePrefixes: [name]} : null); },
      release(name) { emit(name + '-release', null); },
      dispose() { root.removeEventListener('message', receive); }
    };
  };
})(window);
