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

  var packedCols = 0;

  function pack() {
    var cols = columnCount();
    packedCols = cols;
    var occupancy = [];

    function row(r) {
      if (!occupancy[r]) {
        occupancy[r] = [];
        for (var i = 0; i < cols; i += 1) occupancy[r][i] = false;
      }
      return occupancy[r];
    }

    function canPlace(r, c, w, h) {
      if (c + w > cols) return false;
      for (var y = r; y < r + h; y += 1) {
        var cells = row(y);
        for (var x = c; x < c + w; x += 1) {
          if (cells[x]) return false;
        }
      }
      return true;
    }

    function mark(r, c, w, h) {
      for (var y = r; y < r + h; y += 1) {
        var cells = row(y);
        for (var x = c; x < c + w; x += 1) cells[x] = true;
      }
    }

    var ordered = pieces.slice().sort(function (a, b) {
      var aw = Number(a.dataset.cols || 1) * Number(a.dataset.rows || 1);
      var bw = Number(b.dataset.cols || 1) * Number(b.dataset.rows || 1);
      if (bw !== aw) return bw - aw;
      return (b.dataset.tag || "").length - (a.dataset.tag || "").length;
    });

    ordered.forEach(function (piece) {
      var w = Math.min(cols, Math.max(1, Number(piece.dataset.cols || 1)));
      var h = Math.max(1, Number(piece.dataset.rows || 1));
      if (w === cols && h > 1) h = 1;
      var placed = false;
      for (var r = 0; !placed && r < 40; r += 1) {
        for (var c = 0; c <= cols - w; c += 1) {
          if (canPlace(r, c, w, h)) {
            mark(r, c, w, h);
            piece.style.gridColumn = c + 1 + " / span " + w;
            piece.style.gridRow = r + 1 + " / span " + h;
            placed = true;
            break;
          }
        }
      }
    });
  }

  function measure(text, fontFamily, fontSize, width, height, vertical, nowrap) {
    probe.textContent = text;
    probe.style.display = "block";
    probe.style.boxSizing = "border-box";
    probe.style.fontFamily = fontFamily || "sans-serif";
    probe.style.fontSize = fontSize + "px";
    probe.style.fontWeight = "700";
    probe.style.lineHeight = "1";
    probe.style.textAlign = "center";
    probe.style.overflowWrap = "anywhere";
    probe.style.wordBreak = nowrap ? "keep-all" : "break-word";
    probe.style.whiteSpace = nowrap ? "nowrap" : "normal";
    if (vertical) {
      probe.style.writingMode = "vertical-rl";
      probe.style.textOrientation = "mixed";
      probe.style.height = height + "px";
      probe.style.width = "auto";
    } else {
      probe.style.writingMode = "horizontal-tb";
      probe.style.textOrientation = "mixed";
      probe.style.width = width + "px";
      probe.style.height = "auto";
    }
    return {
      w: probe.scrollWidth,
      h: probe.scrollHeight
    };
  }

  function estimateFont(width, height, text, vertical) {
    var chars = Math.max(1, String(text || "").replace(/\s+/g, "").length);
    var run = vertical ? height : width;
    var thick = vertical ? width : height;
    var lo = 6;
    var hi = Math.max(8, Math.min(run / chars * 1.35, thick * 0.84, 72));
    var best = lo;
    for (var i = 0; i < 16; i += 1) {
      var fs = (lo + hi) / 2;
      var charW = fs * 0.72;
      if (chars * charW <= run && fs <= thick) {
        best = fs;
        lo = fs;
      } else {
        hi = fs;
      }
    }
    return best;
  }

  function fitLabel(face) {
    var label = face && face.querySelector(".hero-puzzle__label");
    if (!label) return;
    var piece = face.closest(".hero-puzzle__piece");
    var vertical = piece && piece.getAttribute("data-dir") === "v";
    var width = face.clientWidth - 16;
    var height = face.clientHeight - 16;
    if (width < 4 || height < 4) return;

    var text = (label.textContent || "").replace(/\s+/g, " ").trim();
    var fontFamily = window.getComputedStyle(label).fontFamily;
    var cap = estimateFont(width, height, text, vertical);
    var lo = 6;
    var hi = cap;
    var best = 6;
    var nowrap = true;

    function search(wrap) {
      var localLo = 6;
      var localHi = cap;
      var localBest = 6;
      for (var i = 0; i < 16; i += 1) {
        var mid = (localLo + localHi) / 2;
        var size = measure(text, fontFamily, mid, width, height, vertical, wrap);
        if (size.w <= width + 0.5 && size.h <= height + 0.5) {
          localBest = mid;
          localLo = mid;
        } else {
          localHi = mid;
        }
      }
      return localBest;
    }

    best = search(true);
    if (best <= 7) {
      nowrap = false;
      best = search(false);
    }

    label.style.whiteSpace = nowrap ? "nowrap" : "normal";
    label.style.fontSize = Math.min(best, cap) + "px";
  }

  function fitAll() {
    pieces.forEach(function (piece) {
      fitLabel(piece.querySelector(".hero-puzzle__face--back"));
    });
  }

  function orderByWindows() {
    return pieces.slice().sort(function (a, b) {
      var ar = a.getBoundingClientRect();
      var br = b.getBoundingClientRect();
      if (Math.abs(ar.left - br.left) > 12) return ar.left - br.left;
      return ar.top - br.top;
    });
  }

  function reveal() {
    board.classList.remove("is-sweeping");
    var order = orderByWindows();
    var i = 0;

    function step() {
      if (i >= order.length) {
        later(sweepClose, 7000);
        return;
      }
      order[i].classList.add("is-flipped");
      fitLabel(order[i].querySelector(".hero-puzzle__face--back"));
      i += 1;
      later(step, 170);
    }

    step();
  }

  function sweepClose() {
    board.classList.add("is-sweeping");
    var order = orderByWindows();
    var i = 0;

    function step() {
      if (i >= order.length) {
        board.classList.remove("is-sweeping");
        later(reveal, 520);
        return;
      }
      order[i].classList.remove("is-flipped");
      i += 1;
      later(step, 48);
    }

    step();
  }

  function resetAndPlay() {
    clearTimers();
    pieces.forEach(function (piece) {
      piece.classList.remove("is-flipped");
    });
    pack();
    window.requestAnimationFrame(function () {
      fitAll();
      if (reduce) {
        pieces.forEach(function (piece) {
          piece.classList.add("is-flipped");
        });
        return;
      }
      later(reveal, 900);
    });
  }

  pieces.forEach(function (piece) {
    piece.addEventListener("pointerenter", function () {
      fitLabel(piece.querySelector(".hero-puzzle__face--back"));
    });
  });

  resetAndPlay();
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      fitAll();
    });
  }
  window.addEventListener("load", fitAll);
  var resizeTimer = 0;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      if (columnCount() === packedCols) {
        fitAll();
        return;
      }
      resetAndPlay();
    }, 160);
  });
})();
