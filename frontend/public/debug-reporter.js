/**
 * Client-side error reporter — captures JS errors and sends them to the server
 * so the LLM can debug without needing browser DevTools access.
 * 
 * Injected inline in index.html. Lightweight (~500 bytes minified).
 */
(function() {
  // Don't run twice
  if (window.__debugReporter) return;
  window.__debugReporter = true;

  const endpoint = '/api/v1/debug/log';
  const seen = new Set();
  const queue = [];

  // Flush queue every 30 seconds
  setInterval(() => {
    if (queue.length === 0) return;
    const batch = queue.splice(0);
    try {
      fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({errors: batch}),
        keepalive: true,
      }).catch(() => {});
    } catch(e) {}
  }, 30000);

  function report(level, message, stack) {
    const key = message + (stack || '');
    if (seen.has(key)) return;
    seen.add(key);
    queue.push({
      level,
      message: String(message).slice(0, 500),
      stack: String(stack || '').slice(0, 2000),
      url: location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
    });
  }

  // Capture unhandled errors
  window.addEventListener('error', (e) => {
    report('error', e.message, e.error?.stack);
  });

  // Capture unhandled promise rejections
  window.addEventListener('unhandledrejection', (e) => {
    report('warning', String(e.reason), e.reason?.stack);
  });

  // Capture console errors (if not already captured)
  const origError = console.error;
  console.error = function() {
    const msg = Array.from(arguments).join(' ');
    report('console.error', msg);
    return origError.apply(console, arguments);
  };

  console.log('[DebugReporter] Active — JS errors will be logged to server');
})();
