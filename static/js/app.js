if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  });
}

function clampQuantity(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return 1;
  return Math.min(20, Math.max(1, parsed));
}

document.addEventListener('click', (event) => {
  const actionButton = event.target.closest('[data-qty-action]');
  if (!actionButton) return;

  const control = actionButton.closest('[data-qty-control]');
  const input = control ? control.querySelector('[data-qty-input]') : null;
  if (!input) return;

  const current = clampQuantity(input.value || 1);
  const action = actionButton.getAttribute('data-qty-action');
  input.value = action === 'decrease' ? clampQuantity(current - 1) : clampQuantity(current + 1);
});

document.addEventListener('change', (event) => {
  const input = event.target.closest('[data-qty-input]');
  if (!input) return;
  input.value = clampQuantity(input.value || 1);
});
