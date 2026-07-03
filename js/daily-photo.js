// Sets the homepage hero background to today's calendar-day photo, if one
// exists (see scripts/daily_photos_*.py). Falls back to the plain
// background on days with no photo — this must never break the page.
(async function () {
  const hero = document.getElementById('hero');
  if (!hero) return;

  const today = new Date();
  const dayKey =
    String(today.getMonth() + 1).padStart(2, '0') + '-' +
    String(today.getDate()).padStart(2, '0');

  try {
    const res = await fetch('assets/daily-photos/manifest.json');
    if (!res.ok) return;
    const manifest = await res.json();
    const entry = manifest[dayKey];
    if (!entry) return;

    hero.style.backgroundImage = `url(assets/daily-photos/${dayKey}.jpg)`;
    document.getElementById('hero-overlay').classList.add('visible');

    const bits = [];
    if (entry.location) bits.push(entry.location);
    if (entry.year) bits.push(entry.year);
    const caption = document.getElementById('hero-caption');
    caption.textContent = bits.join(' · ');
    caption.classList.add('visible');
  } catch (e) {
    // no photo today; the plain background is already in place
  }
})();
