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

// Swap favicon instantly when browser color scheme changes.
(function () {
  var dark = "/public/favicon-light.png";
  var light = "/public/favicon.png";

  function setFavicon(isDark) {
    var old = document.querySelector('link[rel="icon"]');
    if (old) old.remove();
    var link = document.createElement("link");
    link.rel = "icon";
    link.type = "image/png";
    link.href = (isDark ? dark : light) + "?v=" + Date.now();
    document.head.appendChild(link);
  }

  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  setFavicon(mq.matches);
  mq.addEventListener("change", function (e) {
    setFavicon(e.matches);
  });
})();
