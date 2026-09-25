(function () {
  var board = document.querySelector(".hero-puzzle__board");
  if (!board) return;

  var pieces = Array.prototype.slice.call(board.querySelectorAll(".hero-puzzle__piece"));
  if (!pieces.length) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var timer = 0;
  var current = null;
  var probe = document.createElement("div");
  probe.setAttribute("aria-hidden", "true");
  probe.style.cssText = "all:initial;position:fixed;left:-12000px;top:0;visibility:hidden;pointer-events:none;";
  document.body.appendChild(probe);

  function estimateFont(width, height, text) {
    var chars = Math.max(1, String(text || "").replace(/\s+/g, "").length);
    var lo = 5;
    var hi = Math.max(6, Math.min(width, height) * 0.9);
    var best = lo;
    for (var i = 0; i < 18; i += 1) {
      var fs = (lo + hi) / 2;
      var charW = fs * 0.7;
      var lineH = fs * 1.12;
      var maxLines = Math.max(1, Math.floor(height / lineH));
      var charsPerLine = Math.max(1, Math.floor(width / charW));
      if (chars <= maxLines * charsPerLine && lineH <= height && charW <= width) {
        best = fs;
        lo = fs;
      } else {
        hi = fs;
      }
    }
    return best;
  }

  function measure(text, fontFamily, width, fontSize) {
    probe.textContent = text;
    probe.style.display = "block";
    probe.style.boxSizing = "border-box";
    probe.style.width = width + "px";
    probe.style.fontFamily = fontFamily || "sans-serif";
    probe.style.fontSize = fontSize + "px";
    probe.style.fontWeight = "700";
    probe.style.lineHeight = "1.05";
    probe.style.textAlign = "center";
    probe.style.whiteSpace = "normal";
    probe.style.overflowWrap = "anywhere";
    probe.style.wordBreak = "break-word";
    return {
      w: probe.scrollWidth,
      h: probe.scrollHeight
    };
  }

  function fitLabel(face) {
    var label = face && face.querySelector(".hero-puzzle__label");
    if (!label) return;
    var width = face.clientWidth - 16;
    var height = face.clientHeight - 16;
    if (width < 4 || height < 4) return;

    var text = (label.textContent || "").replace(/\s+/g, " ").trim();
    var fontFamily = window.getComputedStyle(label).fontFamily;
    var cap = estimateFont(width, height, text);
    var lo = 5;
    var hi = cap;
    var best = Math.min(6, cap);

    for (var i = 0; i < 16; i += 1) {
      var mid = (lo + hi) / 2;
      var size = measure(text, fontFamily, width, mid);
      if (size.w <= width + 0.5 && size.h <= height + 0.5) {
        best = mid;
        lo = mid;
      } else {
        hi = mid;
      }
    }

    label.style.fontSize = Math.min(best, cap) + "px";
  }

  function fitAll() {
    pieces.forEach(function (piece) {
      fitLabel(piece.querySelector(".hero-puzzle__face--back"));
    });
  }

  function clearFlip() {
    if (current) {
      current.classList.remove("is-flipped");
      current = null;
    }
  }

  function pick() {
    var pool = pieces.filter(function (piece) {
      return piece !== current && !piece.matches(":hover");
    });
    if (!pool.length) return null;
    return pool[Math.floor(Math.random() * pool.length)];
  }

  function play() {
    if (reduce) return;
    if (board.matches(":hover")) {
      timer = window.setTimeout(play, 900);
      return;
    }
    clearFlip();
    var next = pick();
    if (!next) {
      timer = window.setTimeout(play, 900);
      return;
    }
    current = next;
    next.classList.add("is-flipped");
    fitLabel(next.querySelector(".hero-puzzle__face--back"));
    timer = window.setTimeout(function () {
      if (next.matches(":hover")) {
        current = null;
        timer = window.setTimeout(play, 400);
        return;
      }
      next.classList.remove("is-flipped");
      current = null;
      timer = window.setTimeout(play, 280);
    }, 5000);
  }

  function scheduleFit() {
    window.requestAnimationFrame(function () {
      fitAll();
      window.requestAnimationFrame(fitAll);
    });
  }

  pieces.forEach(function (piece) {
    piece.addEventListener("pointerenter", function () {
      fitLabel(piece.querySelector(".hero-puzzle__face--back"));
    });
  });

  scheduleFit();
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(scheduleFit);
  }
  window.addEventListener("load", scheduleFit);
  window.addEventListener("resize", function () {
    window.clearTimeout(timer);
    scheduleFit();
    if (!reduce) timer = window.setTimeout(play, 800);
  });

  if (!reduce) {
    timer = window.setTimeout(play, 5000);
  }
})();
