/* Site behaviour: colour scheme, navigation, animated hero field,
   publication filtering. Everything degrades to a usable static page
   if this file fails to load. */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------ theme --- */

  var root = document.documentElement;
  var toggle = document.querySelector("[data-theme-toggle]");

  function currentTheme() {
    var set = root.getAttribute("data-theme");
    if (set) return set;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("kaq-theme", next); } catch (e) {}
      toggle.setAttribute("aria-label", "Switch to " + (next === "dark" ? "light" : "dark") + " mode");
    });
  }

  /* -------------------------------------------------------- navigation --- */

  var navToggle = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector(".site-nav");

  if (navToggle && nav) {
    navToggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        nav.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  var header = document.querySelector("[data-header]");
  if (header) {
    var onScroll = function () { header.classList.toggle("is-stuck", window.scrollY > 8); };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* --------------------------------------------------- metric counters --- */

  var counters = document.querySelectorAll("[data-count-to]");
  if (counters.length && !reduceMotion && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        var el = entry.target;
        var target = parseInt(el.getAttribute("data-count-to"), 10) || 0;
        if (target < 2) return;
        var started = null;
        var duration = 900;
        var step = function (timestamp) {
          if (started === null) started = timestamp;
          var progress = Math.min((timestamp - started) / duration, 1);
          // ease-out cubic
          var eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = String(Math.round(target * eased));
          if (progress < 1) requestAnimationFrame(step);
        };
        el.textContent = "0";
        requestAnimationFrame(step);
      });
    }, { threshold: 0.4 });
    counters.forEach(function (el) { observer.observe(el); });
  }

  /* --------------------------------------------- hero isobar animation --- */

  var canvas = document.querySelector("[data-isobars]");
  if (canvas && !reduceMotion) {
    var ctx = canvas.getContext("2d");
    var width = 0, height = 0, dpr = 1;
    var LINES = 26;

    var resize = function () {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    // Streamlines over a slowly drifting pressure field: a nod to the
    // subtropical-high indices this site's research is built on.
    var draw = function (time) {
      var t = time * 0.00006;
      ctx.clearRect(0, 0, width, height);
      var light = root.getAttribute("data-theme") === "light" ||
        (!root.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: light)").matches);

      for (var i = 0; i < LINES; i++) {
        var ratio = i / (LINES - 1);
        var baseY = height * (0.06 + ratio * 0.95);
        var amp = height * (0.035 + 0.05 * Math.sin(ratio * Math.PI));
        var hue = 168 + ratio * 92;                       // teal -> violet
        var alpha = (light ? 0.16 : 0.24) * (0.35 + 0.65 * Math.sin(ratio * Math.PI));

        ctx.beginPath();
        for (var x = -20; x <= width + 20; x += 12) {
          var u = x / Math.max(width, 1);
          var y = baseY
            + amp * Math.sin(u * 4.1 + t * 1.7 + ratio * 3.4)
            + amp * 0.55 * Math.sin(u * 9.3 - t * 2.3 + ratio * 1.6)
            + amp * 0.3 * Math.cos(u * 2.2 + t * 0.9);
          if (x === -20) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = "hsla(" + hue + ", 78%, " + (light ? 42 : 66) + "%, " + alpha + ")";
        ctx.lineWidth = 1.1;
        ctx.stroke();
      }
      frame = requestAnimationFrame(draw);
    };

    var frame = null;
    resize();
    window.addEventListener("resize", resize);
    frame = requestAnimationFrame(draw);

    // Stop burning frames when the tab is in the background.
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        if (frame) cancelAnimationFrame(frame);
        frame = null;
      } else if (!frame) {
        frame = requestAnimationFrame(draw);
      }
    });
  }

  /* -------------------------------------------------------- blog tags --- */

  var tagBar = document.querySelector("[data-tag-bar]");
  var postGrid = document.querySelector("[data-post-grid]");

  if (tagBar && postGrid) {
    var cards = Array.prototype.slice.call(postGrid.querySelectorAll(".post-card"));
    var postEmpty = document.querySelector("[data-post-empty]");

    tagBar.addEventListener("click", function (event) {
      var button = event.target.closest(".tag-pill");
      if (!button) return;

      tagBar.querySelectorAll(".tag-pill").forEach(function (pill) {
        pill.classList.toggle("is-active", pill === button);
      });

      var tag = button.getAttribute("data-tag");
      var shown = 0;
      cards.forEach(function (card) {
        var match = !tag || (" " + card.dataset.tags + " ").indexOf(" " + tag + " ") !== -1;
        card.hidden = !match;
        if (match) shown++;
      });
      if (postEmpty) postEmpty.hidden = shown !== 0;
    });
  }

  /* ------------------------------------------------ publication filter --- */

  var controls = document.querySelector("[data-pub-controls]");
  var list = document.querySelector("[data-pub-list]");

  if (controls && list) {
    var items = Array.prototype.slice.call(list.querySelectorAll(".pub"));
    var search = controls.querySelector("[data-pub-search]");
    var yearSelect = controls.querySelector("[data-pub-year]");
    var sortSelect = controls.querySelector("[data-pub-sort]");
    var firstOnly = controls.querySelector('[data-pub-filter="first"]');
    var showReview = controls.querySelector('[data-pub-filter="review"]');
    var countEl = controls.querySelector("[data-pub-count]");
    var emptyEl = document.querySelector("[data-pub-empty]");
    var resetBtn = document.querySelector("[data-pub-reset]");

    controls.addEventListener("submit", function (e) { e.preventDefault(); });

    var apply = function () {
      var query = (search.value || "").trim().toLowerCase();
      var year = yearSelect.value;
      var visible = 0;

      items.forEach(function (item) {
        var ok = true;
        if (query && item.dataset.search.indexOf(query) === -1) ok = false;
        if (ok && year && item.dataset.year !== year) ok = false;
        if (ok && firstOnly.checked && item.dataset.first !== "true") ok = false;
        if (ok && !showReview.checked && item.dataset.status === "under_review") ok = false;
        item.hidden = !ok;
        if (ok) visible++;
      });

      if (countEl) {
        countEl.textContent = visible === items.length
          ? "Showing all " + items.length + " entries"
          : "Showing " + visible + " of " + items.length + " entries";
      }
      if (emptyEl) emptyEl.hidden = visible !== 0;
    };

    var sort = function () {
      var mode = sortSelect.value;
      var sorted = items.slice().sort(function (a, b) {
        if (mode === "citations") {
          var diff = Number(b.dataset.citations) - Number(a.dataset.citations);
          if (diff !== 0) return diff;
        }
        return Number(b.dataset.year) - Number(a.dataset.year);
      });
      sorted.forEach(function (item) { list.appendChild(item); });
    };

    [search, yearSelect, firstOnly, showReview].forEach(function (el) {
      el.addEventListener("input", apply);
      el.addEventListener("change", apply);
    });
    sortSelect.addEventListener("change", function () { sort(); apply(); });

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        search.value = "";
        yearSelect.value = "";
        firstOnly.checked = false;
        showReview.checked = true;
        sortSelect.value = "year";
        sort();
        apply();
      });
    }

    apply();
  }
})();
