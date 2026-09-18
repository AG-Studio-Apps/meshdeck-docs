/* meshDeck docs: menu toggles, copy buttons, "On this page". No dependencies. */
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function toggle(button, target) {
    if (!button || !target) return;
    button.addEventListener('click', function () {
      var open = target.classList.toggle('is-open');
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  toggle($('.nav__toggle'), $('#nav-links'));
  toggle($('.sidebar__toggle'), $('#sidebar-list'));

  // Copy buttons on code blocks.
  $$('.prose pre').forEach(function (pre) {
    var btn = document.createElement('button');
    btn.className = 'copy'; btn.type = 'button'; btn.textContent = 'Copy';
    btn.addEventListener('click', function () {
      var code = pre.querySelector('code');
      var text = (code || pre).innerText;
      var done = function () { btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = 'Copy'; }, 1600); };
      if (navigator.clipboard) { navigator.clipboard.writeText(text).then(done, done); } else { done(); }
    });
    pre.appendChild(btn);
  });

  // "On this page" for the manual: built from the h2s, with a scroll spy.
  var body = $('[data-toc]');
  var doc = $('.doc');
  if (body && doc) {
    var heads = $$('h2', body);
    if (heads.length > 1) {
      var aside = document.createElement('aside');
      aside.className = 'on-page'; aside.setAttribute('aria-label', 'On this page');
      aside.innerHTML = '<h4>On this page</h4>';
      var links = heads.map(function (h, i) {
        if (!h.id) h.id = 'section-' + (i + 1);
        var a = document.createElement('a');
        a.href = '#' + h.id; a.textContent = h.textContent;
        aside.appendChild(a);
        return a;
      });
      doc.appendChild(aside);
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (e.isIntersecting) {
              links.forEach(function (l) { l.classList.toggle('is-active', l.getAttribute('href') === '#' + e.target.id); });
            }
          });
        }, { rootMargin: '-15% 0px -70% 0px' });
        heads.forEach(function (h) { io.observe(h); });
      }
    }
  }
})();
