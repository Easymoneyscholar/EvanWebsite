// Fade cards/sections in as they scroll into view
const fadeObserver = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (entry.isIntersecting) entry.target.classList.add('visible');
  }
}, { threshold: 0.2 });

document.querySelectorAll('.fade-in').forEach((el) => fadeObserver.observe(el));
