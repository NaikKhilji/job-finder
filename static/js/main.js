/* ===================================================
   JobFinder — Main JavaScript
   =================================================== */

document.addEventListener('DOMContentLoaded', function () {

  // ===== AUTO-DISMISS TOASTS =====
  const toasts = document.querySelectorAll('.toast');
  toasts.forEach(function (toastEl) {
    const toast = new bootstrap.Toast(toastEl, { delay: 5000, autohide: true });
    toast.show();
  });

  // ===== DARK MODE TOGGLE =====
  const themeToggle = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeIcon');
  const html = document.documentElement;

  const savedTheme = localStorage.getItem('theme') || 'light';
  html.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      const current = html.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      updateThemeIcon(next);
      announce(next === 'dark' ? 'Dark mode enabled' : 'Light mode enabled');
    });
  }

  function updateThemeIcon(theme) {
    if (themeIcon) {
      themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
  }

  // ===== MOBILE SIDEBAR TOGGLE =====
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarClose = document.getElementById('sidebarClose');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');

  function openSidebar() {
    sidebar && sidebar.classList.add('open');
    overlay && overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    sidebarClose && sidebarClose.focus();
  }

  function closeSidebar() {
    sidebar && sidebar.classList.remove('open');
    overlay && overlay.classList.remove('open');
    document.body.style.overflow = '';
    sidebarToggle && sidebarToggle.focus();
  }

  sidebarToggle && sidebarToggle.addEventListener('click', openSidebar);
  sidebarClose && sidebarClose.addEventListener('click', closeSidebar);
  overlay && overlay.addEventListener('click', closeSidebar);

  // Keyboard: close sidebar on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
      closeSidebar();
    }
  });

  // ===== NAVBAR SCROLL EFFECT =====
  const navbar = document.getElementById('mainNav');
  if (navbar) {
    window.addEventListener('scroll', function () {
      navbar.style.boxShadow = window.scrollY > 20
        ? '0 4px 20px rgba(0,0,0,0.08)'
        : 'none';
    }, { passive: true });
  }

  // ===== PASSWORD TOGGLE =====
  window.togglePassword = function (inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
      input.type = 'text';
      icon && (icon.className = 'fas fa-eye-slash');
      btn.setAttribute('aria-label', 'Hide password');
    } else {
      input.type = 'password';
      icon && (icon.className = 'fas fa-eye');
      btn.setAttribute('aria-label', 'Show password');
    }
  };

  // ===== CONFIRM DIALOGS =====
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(el.dataset.confirm)) {
        e.preventDefault();
      }
    });
  });

  // ===== SALARY RANGE DISPLAY =====
  const salaryMin = document.querySelector('input[name="salary_min"]');
  const salaryMax = document.querySelector('input[name="salary_max"]');

  if (salaryMin && salaryMax) {
    function formatSalary(val) {
      return val ? '$' + Number(val).toLocaleString() : '';
    }

    [salaryMin, salaryMax].forEach(function (input) {
      input.addEventListener('input', function () {
        const display = document.getElementById('salaryDisplay');
        if (display) {
          const min = formatSalary(salaryMin.value);
          const max = formatSalary(salaryMax.value);
          if (min && max) display.textContent = min + ' — ' + max;
          else if (min) display.textContent = 'From ' + min;
          else if (max) display.textContent = 'Up to ' + max;
          else display.textContent = '';
        }
      });
    });
  }

  // ===== SMOOTH SCROLL TO ANCHOR =====
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ===== FORM LOADING STATE =====
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
      const btn = form.querySelector('[type="submit"]');
      if (btn && !btn.disabled) {
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processing...';
        btn.setAttribute('aria-busy', 'true');
        setTimeout(function () {
          btn.disabled = false;
          btn.innerHTML = originalText;
          btn.removeAttribute('aria-busy');
        }, 10000);
      }
    });
  });

  // ===== NUMBER COUNTER ANIMATION =====
  const statNumbers = document.querySelectorAll('.stat-number, .stat-card-number');
  const counterObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.textContent.replace(/[^0-9]/g, '')) || 0;
        if (target > 0) animateCounter(el, target);
        counterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  statNumbers.forEach(function (el) { counterObserver.observe(el); });

  function animateCounter(el, target) {
    const duration = 1000;
    const start = performance.now();
    const suffix = el.textContent.replace(/[0-9,]/g, '').trim();

    function update(currentTime) {
      const elapsed = currentTime - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target).toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  // ===== IMAGE PREVIEW HELPER =====
  window.previewImage = function (input, previewId) {
    if (input.files && input.files[0]) {
      const reader = new FileReader();
      reader.onload = function (e) {
        const preview = document.getElementById(previewId);
        if (preview) {
          preview.src = e.target.result;
          preview.style.display = 'block';
        }
      };
      reader.readAsDataURL(input.files[0]);
    }
  };

  // ===== ACTIVE NAV LINK HIGHLIGHT =====
  const currentPath = window.location.pathname;
  document.querySelectorAll('.sidebar-link').forEach(function (link) {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // ===== SEARCH DEBOUNCE (jobs listing) =====
  const searchInput = document.querySelector('.jobs-page input[name="search"]');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        const form = searchInput.closest('form');
        if (form && searchInput.value.length >= 2) {
          form.submit();
        }
      }, 600);
    });
  }

  // ===== ACTIVE FILTER COUNT BADGE =====
  const filterToggleBtn = document.querySelector('.filter-toggle-btn');
  if (filterToggleBtn) {
    const urlParams = new URLSearchParams(window.location.search);
    const filterKeys = ['job_type', 'location', 'experience', 'salary_min', 'salary_max'];
    const activeCount = filterKeys.filter(k => urlParams.get(k) && urlParams.get(k) !== '0').length;

    if (activeCount > 0) {
      const existingBadge = filterToggleBtn.querySelector('.badge');
      if (existingBadge) {
        existingBadge.textContent = activeCount;
        existingBadge.className = 'badge bg-primary ms-auto filter-count-badge';
      } else {
        const badge = document.createElement('span');
        badge.className = 'badge bg-primary ms-auto filter-count-badge';
        badge.textContent = activeCount;
        badge.setAttribute('aria-label', activeCount + ' active filters');
        filterToggleBtn.appendChild(badge);
      }
    }
  }

  // ===== SCREEN READER ANNOUNCER =====
  function announce(message) {
    const announcer = document.getElementById('sr-announcer');
    if (announcer) {
      announcer.textContent = '';
      setTimeout(() => { announcer.textContent = message; }, 100);
    }
  }
  window.srAnnounce = announce;

  // ===== MODAL FOCUS TRAP =====
  document.querySelectorAll('.modal').forEach(function (modal) {
    modal.addEventListener('shown.bs.modal', function () {
      const focusable = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length) focusable[0].focus();
    });
  });

});
