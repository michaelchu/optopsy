// After a thread is deleted, navigate to a fresh chat instead of leaving
// the UI showing the stale deleted conversation.
(function () {
  const _fetch = window.fetch;
  window.fetch = function (input, init) {
    const url = typeof input === "string" ? input : input?.url ?? "";
    const method = (init?.method ?? "GET").toUpperCase();
    const promise = _fetch.apply(this, arguments);
    if (method === "DELETE" && url.includes("/project/thread")) {
      promise.then((res) => {
        if (res.ok) {
          window.location.href = "/";
        }
      });
    }
    return promise;
  };
})();
