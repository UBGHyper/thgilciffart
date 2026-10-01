(function () {
  "use strict";

  var FACULTIES = [
    ["Mathematics", ["Mathematics Standard", "Mathematics Advanced", "Mathematics Extension 1", "Mathematics Extension 2"]],
    ["Science", ["Biology", "Chemistry", "Physics", "Earth and Environmental Science", "Senior Science"]],
    ["English", ["English (Paper 1)", "English (Paper 2)"]],
    ["HSIE", ["Ancient History", "Modern History", "History Extension", "Business Studies", "Economics", "Legal Studies", "Studies of Religion I", "Studies of Religion II"]],
    ["TAS", ["Agriculture", "Engineering Studies", "Information Processes and Technology", "Software Design and Development"]],
    ["PDHPE and CAFS", ["PDHPE", "Community and Family Studies"]],
    ["Other", ["Miscellaneous"]]
  ];

  var app = document.getElementById("app");
  var crumbs = document.getElementById("crumbs");
  var search = document.getElementById("search");
  var themeBtn = document.getElementById("theme-toggle");

  var subjects = [];
  var cache = {};

  function theme() { return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light"; }
  function syncThemeBtn() { themeBtn.textContent = theme() === "dark" ? "light" : "dark"; }
  themeBtn.addEventListener("click", function () {
    var t = theme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("papersdb-theme", t); } catch (e) {}
    syncThemeBtn();
  });
  syncThemeBtn();

  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    for (var k in attrs || {}) el.setAttribute(k, attrs[k]);
    (kids || []).forEach(function (c) {
      if (c != null) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return el;
  }

  function size(s) {
    if (typeof s === "number") return Math.max(1, Math.round(s / 1024)) + " KB";
    return s || "";
  }

  function table(headers, rows) {
    return h("div", { class: "box" }, [
      h("table", {}, [
        h("thead", {}, [h("tr", {}, headers)]),
        h("tbody", {}, rows)
      ])
    ]);
  }

  function setCrumbs(name) {
    crumbs.innerHTML = "";
    if (name) crumbs.appendChild(h("span", {}, [h("span", { class: "sep" }, ["/"]), name]));
  }

  function grouped(list) {
    var byName = {}, used = {};
    list.forEach(function (s) { byName[s.name] = s; });
    var out = FACULTIES.map(function (f) {
      var items = f[1].map(function (n) { used[n] = 1; return byName[n]; }).filter(Boolean);
      return [f[0], items];
    });
    var rest = list.filter(function (s) { return !used[s.name]; });
    if (rest.length) out.push(["Other", rest]);
    return out.filter(function (g) { return g[1].length; });
  }

  function renderHome() {
    setCrumbs(null);
    app.innerHTML = "";
    var q = search.value.trim().toLowerCase();
    var list = subjects.filter(function (s) { return !q || s.name.toLowerCase().indexOf(q) !== -1; });
    var groups = grouped(list);
    if (!groups.length) { app.appendChild(h("p", { class: "empty" }, ["No matches."])); return; }
    groups.forEach(function (g) {
      app.appendChild(h("div", { class: "gtitle" }, [g[0]]));
      app.appendChild(table(
        [h("th", {}, ["Name"]), h("th", { class: "r num-col" }, ["Papers"]), h("th", { class: "r num-col hide-sm" }, ["Schools"])],
        g[1].map(function (s) {
          return h("tr", {}, [
            h("td", {}, [h("a", { href: "#/" + s.slug }, [s.name])]),
            h("td", { class: "r num" }, [String(s.paperCount)]),
            h("td", { class: "r num hide-sm" }, [String(s.schoolCount)])
          ]);
        })
      ));
    });
  }

  function paperRows(papers, external) {
    return papers.map(function (p) {
      var a = h("a", { href: p.url }, [p.title]);
      if (external) { a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener"); }
      return h("tr", {}, [
        h("td", {}, [a]),
        h("td", { class: "num hide-sm" }, [p.modified || ""]),
        h("td", { class: "r num" }, [size(p.size)])
      ]);
    });
  }

  function group(title, papers, external) {
    app.appendChild(h("div", { class: "gtitle" }, [title]));
    app.appendChild(table(
      [h("th", {}, ["Name"]), h("th", { class: "hide-sm" }, ["Modified"]), h("th", { class: "r" }, ["Size"])],
      paperRows(papers, external)
    ));
  }

  function renderSubject(s) {
    app.innerHTML = "";
    var q = search.value.trim().toLowerCase();
    var ext = !s.native;
    var match = function (p) { return !q || p.title.toLowerCase().indexOf(q) !== -1; };
    s.categories.forEach(function (cat) {
      var flat = cat.papers.filter(match);
      if (flat.length) group(cat.name, flat, ext);
      cat.schools.forEach(function (sc) {
        var hit = q && sc.name.toLowerCase().indexOf(q) !== -1;
        var papers = hit ? sc.papers : sc.papers.filter(match);
        if (papers.length) group(cat.name + " / " + sc.name, papers, ext);
      });
    });
    if (!app.children.length) app.appendChild(h("p", { class: "empty" }, ["No matches."]));
  }

  function render() {
    var slug = location.hash.replace(/^#\/?/, "").split("/")[0];
    var entry = subjects.filter(function (s) { return s.slug === slug; })[0];
    if (!entry) { renderHome(); return; }
    setCrumbs(entry.name);
    if (cache[slug]) { renderSubject(cache[slug]); return; }
    app.innerHTML = "";
    fetch("data/subjects/" + slug + ".json")
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (full) { cache[slug] = full; renderSubject(full); })
      .catch(function () { app.innerHTML = ""; app.appendChild(h("p", { class: "empty" }, ["Couldn't load this subject."])); });
  }

  var t;
  search.addEventListener("input", function () { clearTimeout(t); t = setTimeout(render, 100); });
  window.addEventListener("hashchange", function () { search.value = ""; render(); });

  fetch("data/manifest.json")
    .then(function (r) { return r.json(); })
    .then(function (m) { subjects = m.subjects; render(); })
    .catch(function () { app.appendChild(h("p", { class: "empty" }, ["Couldn't load data."])); });
})();
