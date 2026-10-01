(function () {
  var board = document.querySelector(".hero-puzzle__board");
  if (!board) return;

  var pieces = Array.prototype.slice.call(board.querySelectorAll(".hero-puzzle__piece"));
  if (!pieces.length) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var timers = [];

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

  function shuffle(list) {
    var arr = list.slice();
    for (var i = arr.length - 1; i > 0; i -= 1) {
      var j = Math.floor(Math.random() * (i + 1));
      var swap = arr[i];
      arr[i] = arr[j];
      arr[j] = swap;
    }
    return arr;
  }

  function reveal() {
    board.classList.remove("is-closing");
    indexPieces();
    var order = shuffle(pieces);
    var i = 0;

    function step() {
      if (i >= order.length) {
        later(dominoClose, 7000);
        return;
      }
      order[i].classList.add("is-flipped");
      i += 1;
      later(step, 3000);
    }

    step();
  }

  function dominoClose() {
    board.classList.add("is-closing");
    indexPieces();
    var order = pieces.slice().sort(function (a, b) {
      var aSum = Number(a.dataset.r) + Number(a.dataset.c);
      var bSum = Number(b.dataset.r) + Number(b.dataset.c);
      if (aSum !== bSum) return aSum - bSum;
      if (Number(a.dataset.r) !== Number(b.dataset.r)) return Number(a.dataset.r) - Number(b.dataset.r);
      return Number(a.dataset.c) - Number(b.dataset.c);
    });
    var i = 0;

    function step() {
      if (i >= order.length) {
        later(function () {
          board.classList.remove("is-closing");
          later(reveal, 500);
        }, 420);
        return;
      }
      order[i].classList.remove("is-flipped");
      i += 1;
      later(step, 70);
    }

    step();
  }

  function resetAndPlay() {
    clearTimers();
    board.classList.remove("is-closing");
    pieces.forEach(function (piece) {
      piece.classList.remove("is-flipped");
    });
    indexPieces();
    if (reduce) {
      pieces.forEach(function (piece) {
        piece.classList.add("is-flipped");
      });
      return;
    }
    later(reveal, 800);
  }

  resetAndPlay();

  var resizeTimer = 0;
  var lastCols = columnCount();
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      var cols = columnCount();
      if (cols === lastCols) return;
      lastCols = cols;
      resetAndPlay();
    }, 160);
  });
})();
