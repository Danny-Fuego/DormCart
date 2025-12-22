/* NAVBAR drawer logic ----------------
   This script controls the mobile navigation drawer and search validation.
   I used AI assistance mainly to structure the logic cleanly, handle edge
   cases (like closing on overlay click / Escape key), and improve accessibility
   (aria-expanded handling). The final implementation and integration were done
   by me.
*/

const menuBtn   = document.querySelector('.menu-btn');
const drawer    = document.getElementById('mobileDrawer');
const overlay   = document.getElementById('navOverlay');

/* Centralized close function so all close actions
   (overlay click, link click, Escape key) behave consistently */
function closeDrawer(){
    drawer.classList.remove('open');
    overlay.classList.remove('show');
    menuBtn.setAttribute('aria-expanded','false');
}

/* Toggle drawer when hamburger menu is clicked */
menuBtn.addEventListener('click', () => {
    const isOpen = !drawer.classList.contains('open');

    if (isOpen) {
        drawer.classList.add('open');
        overlay.classList.add('show');
    } else {
        drawer.classList.remove('open');
        overlay.classList.remove('show');
    }

    // Accessibility: reflect drawer state for screen readers
    menuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
});

/* Close drawer when clicking outside it */
overlay.addEventListener('click', closeDrawer);

/* Close drawer when a navigation link is clicked */
drawer.addEventListener('click', (e) => {
    if (e.target.matches('a')) closeDrawer();
});

/* Close drawer with Escape key for keyboard users */
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDrawer();
});

/* Search form validation (desktop + mobile)
   AI helped suggest a small reusable pattern instead of duplicating logic.
   This prevents empty searches and improves UX. */
document.addEventListener("DOMContentLoaded", () => {
  const pairs = [
    ["searchForm", "searchInput"],
    ["searchFormMobile", "searchInputMobile"],
  ];

  pairs.forEach(([formId, inputId]) => {
    const form = document.getElementById(formId);
    const input = document.getElementById(inputId);
    if (!form || !input) return;

    form.addEventListener("submit", (e) => {
      if (!input.value.trim()) {
        e.preventDefault();
        input.focus();
      }
    });
  });
});