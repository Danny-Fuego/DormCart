(function () {
  const wrap = document.getElementById("toastWrap");
  if (!wrap) return;

  const TOAST_MS = 3500; // auto-hide time
  const REMOVE_MS = 220; // must match CSS transition

  function dismiss(toast) {
    toast.classList.add("hide");
    setTimeout(() => toast.remove(), REMOVE_MS);
  }

  // manual close
  wrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".toast-close");
    if (!btn) return;
    dismiss(btn.closest(".toast"));
  });

  // auto dismiss
  wrap.querySelectorAll(".toast").forEach((toast) => {
    let t = setTimeout(() => dismiss(toast), TOAST_MS);

    // pause on hover (optional but clean UX)
    toast.addEventListener("mouseenter", () => clearTimeout(t));
    toast.addEventListener("mouseleave", () => {
      t = setTimeout(() => dismiss(toast), 1200);
    });
  });
})();