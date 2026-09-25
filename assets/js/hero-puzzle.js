(function () {
  var board = document.querySelector(".hero-puzzle__board");
  if (!board) return;

  var pieces = Array.prototype.slice.call(board.querySelectorAll(".hero-puzzle__piece"));
  if (!pieces.length) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var timers = [];
  var probe = document.createElement("div");
  probe.setAttribute("aria-hidden", "true");
  probe.style.cssText = "all:initial;position:fixed;left:-12000px;top:0;visibility:hidden;pointer-events:none;";
  document.body.appendChild(probe);

  function later(fn, ms) {
    var id = window.setTimeout(fn, ms);
    timers.push(id);
    return id;
  }

  function clearTimers() {
    timers.forEach(function (id) {
      window.clearTimeout(id);
    });
    timers = [];
  }

  function columnCount() {
    var cols = window.getComputedStyle(board).gridTemplateColumns;
    return Math.max(1, cols.split(" ").length);
  }

  function indexPieces() {
    var cols = columnCount();
    pieces.forEach(function (piece, i) {
      piece.dataset.c = String(i % cols);
      piece.dataset.r = String(Math.floor(i / cols));
    });
  }

  function measure(text, fontFamily, fontSize, width, height, nowrap) {
    probe.textContent = text;
    probe.style.display = "block";
    probe.style.boxSizing = "border-box";
    probe.style.fontFamily = fontFamily || "sans-serif";
    probe.style.fontSize = fontSize + "px";
    probe.style.fontWeight = "700";
    probe.style.lineHeight = "1.05";
    probe.style.textAlign = "center";
    probe.style.writingMode = "horizontal-tb";
    probe.style.overflowWrap = "anywhere";
    probe.style.wordBreak = nowrap ? "keep-all" : "break-word";
    probe.style.whiteSpace = nowrap ? "nowrap" : "normal";
    probe.style.width = width + "px";
    probe.style.height = "auto";
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
    var chars = Math.max(1, text.replace(/\s+/g, "").length);
    var cap = Math.max(8, Math.min(width / chars * 1.4, height * 0.72, 64));

    function search(nowrap) {
      var lo = 6;
      var hi = cap;
      var best = 6;
      for (var i = 0; i < 16; i += 1) {
        var mid = (lo + hi) / 2;
        var size = measure(text, fontFamily, mid, width, height, nowrap);
        if (size.w <= width + 0.5 && size.h <= height + 0.5) {
          best = mid;
          lo = mid;
        } else {
          hi = mid;
        }
      }
      return best;
    }

    var nowrap = true;
    var best = search(true);
    if (best <= 8) {
      nowrap = false;
      best = search(false);
    }

    label.style.whiteSpace = nowrap ? "nowrap" : "normal";
    label.style.fontSize = best + "px";
  }

  function fitAll() {
    pieces.forEach(function (piece) {
      fitLabel(piece.querySelector(".hero-puzzle__face--back"));
    });
  }

  function revealOrder() {
    return pieces.slice().sort(function (a, b) {
      var ar = Number(a.dataset.r);
      var br = Number(b.dataset.r);
      if (ar !== br) return ar - br;
      return Number(a.dataset.c) - Number(b.dataset.c);
    });
  }

  function reveal() {
    board.classList.remove("is-closing");
    indexPieces();
    var order = revealOrder();
    var i = 0;

    function step() {
      if (i >= order.length) {
        later(dominoClose, 7000);
        return;
      }
      order[i].classList.add("is-flipped");
      fitLabel(order[i].querySelector(".hero-puzzle__face--back"));
      i += 1;
      later(step, 160);
    }

    step();
  }

  function dominoClose() {
    board.classList.add("is-closing");
    indexPieces();
    var byKey = {};
    pieces.forEach(function (piece) {
      byKey[piece.dataset.r + ":" + piece.dataset.c] = piece;
    });

    var start = byKey["0:0"] || pieces[0];
    var seen = {};
    var waves = [[start]];
    seen[start.dataset.r + ":" + start.dataset.c] = true;

    for (var w = 0; w < waves.length; w += 1) {
      var next = [];
      waves[w].forEach(function (piece) {
        var r = Number(piece.dataset.r);
        var c = Number(piece.dataset.c);
        [[0, 1], [1, 0]].forEach(function (delta) {
          var key = r + delta[0] + ":" + (c + delta[1]);
          if (byKey[key] && !seen[key]) {
            seen[key] = true;
            next.push(byKey[key]);
          }
        });
      });
      if (next.length) waves.push(next);
    }

    waves.forEach(function (wave, index) {
      later(function () {
        wave.forEach(function (piece) {
          piece.classList.remove("is-flipped");
        });
        if (index === waves.length - 1) {
          later(function () {
            board.classList.remove("is-closing");
            later(reveal, 480);
          }, 360);
        }
      }, index * 75);
    });
  }

  function resetAndPlay() {
    clearTimers();
    board.classList.remove("is-closing");
    pieces.forEach(function (piece) {
      piece.classList.remove("is-flipped");
    });
    indexPieces();
    window.requestAnimationFrame(function () {
      fitAll();
      if (reduce) {
        pieces.forEach(function (piece) {
          piece.classList.add("is-flipped");
        });
        return;
      }
      later(reveal, 800);
    });
  }

  resetAndPlay();
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(fitAll);
  }
  window.addEventListener("load", fitAll);

  var resizeTimer = 0;
  var lastCols = columnCount();
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      var cols = columnCount();
      if (cols === lastCols) {
        fitAll();
        return;
      }
      lastCols = cols;
      resetAndPlay();
    }, 160);
  });
})();
