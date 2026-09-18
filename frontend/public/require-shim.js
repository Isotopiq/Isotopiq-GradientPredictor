// Shim Node.js require() for browser — ketcher-standalone has baked-in require calls.
// External file (not inline) so the Content-Security-Policy can stay strict.
window.__nodeShims = true;
var __moduleCache = {};
window.require = function (name) {
  if (__moduleCache[name]) return __moduleCache[name].exports;
  var mod = { exports: {} };
  __moduleCache[name] = mod;
  // Return stub for Node.js built-ins and packages that don't exist in browser
  if (name === 'util') {
    mod.exports = { types: {}, inspect: function (o) { return String(o); }, isArray: Array.isArray };
  } else if (name === 'raphael') {
    mod.exports = {};
  } else if (name === 'ajv/dist/runtime/ucs2length') {
    mod.exports = function (str) { return str.length; };
  } else {
    mod.exports = {};
  }
  return mod.exports;
};
