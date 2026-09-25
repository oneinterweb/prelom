(function () {
  var board = document.querySelector(".hero-puzzle__board");
  if (!board) return;

  var pieces = Array.prototype.slice.call(board.querySelectorAll(".hero-puzzle__piece"));
  if (!pieces.length) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var timer = 0;
  var current = null;
  var probe = document.createElement("span");
  probe.setAttribute("aria-hidden", "true");
  probe.style.cssText = [
    "position:absolute",
    "left:-9999px",
    "top:0",
    "display:block",
    "box-sizing:border-box",
    "line-height:1.05",
    "font-weight:700",
    "text-align:center",
    "white-space:normal",
    "word-break:break-word",
    "overflow-wrap:anywhere",
    "pointer-events:none"
  ].join(";");
  document.body.appendChild(probe);

  function fitLabel(face) {
    var label = face && face.querySelector(".hero-puzzle__label");
    if (!label) return;
    var width = face.clientWidth - 8;
    var height = face.clientHeight - 8;
    if (width < 4 || height < 4) return;

    var styles = window.getComputedStyle(label);
    probe.style.fontFamily = styles.fontFamily;
    probe.style.letterSpacing = styles.letterSpacing;
    probe.style.width = width + "px";
    probe.textContent = label.textContent;

    var lo = 6;
    var hi = Math.max(8, Math.min(width, height) * 0.72);
    var best = lo;

    for (var i = 0; i < 18; i += 1) {
      var mid = (lo + hi) / 2;
      probe.style.fontSize = mid + "px";
      if (probe.scrollWidth <= width + 0.5 && probe.scrollHeight <= height + 0.5) {
        best = mid;
        lo = mid;
      } else {
        hi = mid;
      }
    }

    label.style.fontSize = best + "px";
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
    }, 1500);
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
