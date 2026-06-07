document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.open-dialog').forEach(button => {
    button.addEventListener('click', () => {
      const target = document.getElementById(button.dataset.target);
      if (target) target.classList.add('active');
    });
  });
  document.querySelectorAll('.close-dialog').forEach(button => {
    button.addEventListener('click', () => button.closest('.dialog').classList.remove('active'));
  });
  document.querySelectorAll('.dialog').forEach(dialog => {
    dialog.addEventListener('click', event => {
      if (event.target === dialog) dialog.classList.remove('active');
    });
  });
});
