// Simple hero slider
document.addEventListener('DOMContentLoaded', () => {
  const slides = Array.from(document.querySelectorAll('.slide'));
  const dotsWrap = document.getElementById('dots');
  const prev = document.getElementById('prev');
  const next = document.getElementById('next');
  let idx = 0;
  if (!slides.length) return;

  // create dots
  slides.forEach((s, i) => {
    const d = document.createElement('span');
    d.className = 'dot' + (i === 0 ? ' active' : '');
    d.dataset.index = i;
    d.addEventListener('click', () => { showSlide(i); });
    dotsWrap.appendChild(d);
  });

  function showSlide(i) {
    slides.forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.dot').forEach(d => d.classList.remove('active'));
    slides[i].classList.add('active');
    document.querySelectorAll('.dot')[i].classList.add('active');
    idx = i;
  }

  // next/prev
  if (next) next.addEventListener('click', () => showSlide((idx + 1) % slides.length));
  if (prev) prev.addEventListener('click', () => showSlide((idx - 1 + slides.length) % slides.length));

  // auto-play
  setInterval(() => showSlide((idx + 1) % slides.length), 4500);

  // initialize
  showSlide(0);
});
