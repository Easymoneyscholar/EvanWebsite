// Faint background mosaic of random Wikipedia article thumbnails.
// Purely decorative — fails silently if Wikipedia is unreachable.
(async function () {
  const container = document.createElement('div');
  container.className = 'wiki-bg';
  container.setAttribute('aria-hidden', 'true');
  document.body.prepend(container);

  // Wikipedia's pageimages lookup only resolves for the first ~50 generated
  // pages per request regardless of grnlimit, and only ~20% of articles have
  // a thumbnail at all — so fire several requests instead of one big one.
  const TARGET_IMAGES = 60;
  const MAX_REQUESTS = 6;
  const endpoint =
    'https://en.wikipedia.org/w/api.php?action=query&generator=random' +
    '&grnnamespace=0&grnlimit=50' +
    '&prop=pageimages&piprop=thumbnail&pithumbsize=200' +
    '&format=json&origin=*';

  let collected = 0;
  for (let i = 0; i < MAX_REQUESTS && collected < TARGET_IMAGES; i++) {
    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      const pages = Object.values(data.query?.pages || {});
      for (const page of pages) {
        const thumb = page.thumbnail;
        if (!thumb) continue;
        const img = document.createElement('img');
        img.src = thumb.source;
        img.loading = 'lazy';
        img.alt = '';
        container.appendChild(img);
        collected++;
      }
    } catch (e) {
      break; // no background today; the site still works fine without it
    }
  }
})();
