# Book website

`frontend/` is the website. It is generated, so don't edit its pages by hand.

- Topic pages live in `chapter-NN-*/<topic>/`.
- `scripts/book.json` sets the order of chapters, topics and pages.
- Rebuild after adding or changing pages:

```
python3 scripts/build-book.py
```

To preview locally: `cd frontend && python3 -m http.server 8000`, then open http://localhost:8000.

To host: point any static host (Netlify, Cloudflare Pages, Vercel) at the `frontend/` folder. No build step is needed on the host.
