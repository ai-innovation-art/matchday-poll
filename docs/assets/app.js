(function () {
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage may be blocked */ } }
  };

  // theme toggle: system -> light -> dark
  var root = document.documentElement;
  var saved = store.get("poll-theme");
  if (saved) root.setAttribute("data-theme", saved);
  var themeBtn = document.getElementById("theme");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var cur = root.getAttribute("data-theme");
      var next = cur === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      store.set("poll-theme", next);
    });
  }

  // mobile navigation
  var open = document.getElementById("nav-open");
  if (open) open.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
  document.addEventListener("click", function (e) {
    if (document.body.classList.contains("nav-open") && !e.target.closest(".side") && e.target.id !== "nav-open") {
      document.body.classList.remove("nav-open");
    }
  });

  // copy buttons on code blocks
  document.querySelectorAll("pre").forEach(function (pre) {
    var btn = document.createElement("button");
    btn.className = "copy"; btn.type = "button"; btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var text = pre.querySelector("code").innerText;
      var done = function () { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy"; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { btn.textContent = "Select + Ctrl+C"; });
      } else { btn.textContent = "Select + Ctrl+C"; }
    });
    pre.appendChild(btn);
  });

  // remember which missions are done (in this browser only)
  var page = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".mission").forEach(function (m) {
    var key = "poll-done:" + page + "#" + m.id;
    var box = m.querySelector(".done input");
    if (!box) return;
    if (store.get(key) === "1") { box.checked = true; m.classList.add("is-done"); }
    box.addEventListener("change", function () {
      m.classList.toggle("is-done", box.checked);
      store.set(key, box.checked ? "1" : "0");
    });
  });
})();
