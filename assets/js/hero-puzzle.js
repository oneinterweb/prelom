(function () {
  var root = document.querySelector(".hero-puzzle");
  if (!root) return;

  var dataEl = document.getElementById("hero-puzzle-data");
  var board = root.querySelector("[data-puzzle-board]");
  var frame = root.querySelector(".hero-puzzle__frame");
  var photo = root.querySelector(".hero-puzzle__photo");
  if (!dataEl || !board || !frame) return;

  var tags;
  try {
    tags = JSON.parse(dataEl.textContent);
  } catch (err) {
    return;
  }
  if (!tags || !tags.length) return;

  function spanFor(count) {
    if (count >= 15) return 5;
    if (count >= 9) return 4;
    if (count >= 4) return 3;
    if (count >= 2) return 2;
    return 1;
  }

  var pieces = tags
    .map(function (tag) {
      return {
        name: tag.name,
        label: tag.label,
        url: tag.url,
        count: tag.count,
        span: spanFor(tag.count)
      };
    })
    .sort(function (a, b) {
      if (b.span !== a.span) return b.span - a.span;
      if (b.count !== a.count) return b.count - a.count;
      return a.name.localeCompare(b.name, "bg");
    });

  function pack(items, cols) {
    var occ = [];
    var rows = 0;

    function occupied(r, c) {
      return occ[r] && occ[r][c];
    }

    function mark(r, c, span) {
      for (var i = 0; i < span; i += 1) {
        occ[r + i] = occ[r + i] || [];
        for (var j = 0; j < span; j += 1) occ[r + i][c + j] = true;
      }
    }

    function fits(r, c, span) {
      if (c + span > cols) return false;
      for (var i = 0; i < span; i += 1) {
        for (var j = 0; j < span; j += 1) {
          if (occupied(r + i, c + j)) return false;
        }
      }
      return true;
    }

    items.forEach(function (item) {
      var placed = false;
      var r = 0;
      while (!placed) {
        for (var c = 0; c <= cols - item.span; c += 1) {
          if (fits(r, c, item.span)) {
            item.col = c;
            item.row = r;
            mark(r, c, item.span);
            if (r + item.span > rows) rows = r + item.span;
            placed = true;
            break;
          }
        }
        r += 1;
        if (r > 200) break;
      }
    });

    return rows;
  }

  function columnCount(width) {
    if (width < 520) return 14;
    if (width < 800) return 20;
    return 26;
  }

  var nodes = [];
  var flipTimers = [];

  function paintBackgrounds() {
    var boardBox = board.getBoundingClientRect();
    if (!boardBox.width || !boardBox.height) return;
    nodes.forEach(function (node) {
      var front = node.querySelector(".hero-puzzle__face--front");
      var box = node.getBoundingClientRect();
      front.style.backgroundImage = 'url("' + root.getAttribute("data-hero-src") + '")';
      front.style.backgroundSize = boardBox.width + "px " + boardBox.height + "px";
      front.style.backgroundPosition =
        "-" + (box.left - boardBox.left) + "px -" + (box.top - boardBox.top) + "px";
    });
  }

  function render() {
    var cols = columnCount(frame.clientWidth || root.clientWidth || 960);
    var rows = pack(pieces, cols);
    frame.style.aspectRatio = cols + " / " + rows;
    board.style.setProperty("--puzzle-cols", String(cols));
    board.style.setProperty("--puzzle-rows", String(rows));
    board.replaceChildren();
    nodes = [];

    pieces.forEach(function (piece) {
      var link = document.createElement("a");
      link.className = "hero-puzzle__piece";
      link.href = piece.url;
      link.setAttribute("rel", "tag");
      link.style.gridColumn = piece.col + 1 + " / span " + piece.span;
      link.style.gridRow = piece.row + 1 + " / span " + piece.span;
      link.title = piece.label + " · " + piece.count;
      link.setAttribute("data-span", String(piece.span));

      var inner = document.createElement("span");
      inner.className = "hero-puzzle__inner";

      var front = document.createElement("span");
      front.className = "hero-puzzle__face hero-puzzle__face--front";
      front.setAttribute("aria-hidden", "true");

      var back = document.createElement("span");
      back.className = "hero-puzzle__face hero-puzzle__face--back";
      back.textContent = piece.label;

      inner.appendChild(front);
      inner.appendChild(back);
      link.appendChild(inner);
      board.appendChild(link);
      nodes.push(link);
    });

    window.requestAnimationFrame(paintBackgrounds);
  }

  function flip(node, on) {
    if (!node) return;
    node.classList.toggle("is-flipped", on);
  }

  function reveal(node) {
    flip(node, true);
    var idx = nodes.indexOf(node);
    if (idx === -1) return;
    window.clearTimeout(flipTimers[idx]);
    flipTimers[idx] = window.setTimeout(function () {
      if (!node.matches(":hover, :focus-visible")) flip(node, false);
    }, 900);
  }

  function pieceFromPoint(x, y) {
    var el = document.elementFromPoint(x, y);
    if (!el) return null;
    return el.closest(".hero-puzzle__piece");
  }

  board.addEventListener("pointermove", function (event) {
    var piece = pieceFromPoint(event.clientX, event.clientY);
    if (piece) reveal(piece);
  });

  board.addEventListener("pointerleave", function () {
    nodes.forEach(function (node, idx) {
      window.clearTimeout(flipTimers[idx]);
      flipTimers[idx] = window.setTimeout(function () {
        flip(node, false);
      }, 250);
    });
  });

  board.addEventListener("focusin", function (event) {
    var piece = event.target.closest(".hero-puzzle__piece");
    if (piece) flip(piece, true);
  });

  board.addEventListener("focusout", function (event) {
    var piece = event.target.closest(".hero-puzzle__piece");
    if (piece) flip(piece, false);
  });

  render();

  var resizeTimer;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      render();
    }, 120);
  });

  if (photo && photo.complete) paintBackgrounds();
  else if (photo) photo.addEventListener("load", paintBackgrounds);
})();
