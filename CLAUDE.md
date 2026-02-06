# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Static website for **Bartusch - Holz und Handwerk** (a German carpentry business), built with Jekyll 4.4.1. No JavaScript frameworks — pure HTML/SCSS with minimal vanilla JS (theme toggle + GLightbox). German language content throughout.

## Development Commands

```bash
bundle install --path vendor/bundle   # Install Ruby dependencies
./scripts/download-videos.sh           # Fetch videos from Nextcloud (required before build)
bundle exec jekyll serve               # Dev server at http://localhost:4000
bundle exec jekyll build               # Production build → _site/
```

Videos are stored externally on Nextcloud and listed in `videos.manifest` (tab-separated: `local_path\tnextcloud_url`). They must be downloaded before building.

## Git Workflow

**Never push to remote without asking first.** Always confirm with the user before running `git push`.

## Architecture

**Static site generation** — Jekyll processes Markdown/HTML → static HTML at build time. No runtime rendering, no database, no backend.

### Key Directories

- `_pages/` — Content pages (Markdown with YAML front matter). Services are nested under `_pages/leistungen/`.
- `_layouts/` — `default.html` (base shell with header/footer) and `page.html` (content wrapper).
- `_includes/` — Shared components: `nav.html` (desktop dropdown), `mobile-nav.html` (CSS-only drawer), `footer.html`.
- `_sass/` — Modular SCSS: `_variables.scss` (colors, breakpoints), `_base.scss`, `_nav.scss`, `_mobile.scss`, `_layout.scss`.
- `assets/css/main.scss` — Single SCSS entry point that imports all partials.
- `assets/vendor/` — Self-hosted GLightbox and Material Design Icons (MDI).

### Styling

Custom SCSS compiled to a single compressed CSS file. No CSS framework.

- Single responsive breakpoint at **768px** (mobile-first)
- **Dark mode**: CSS custom properties toggled via `data-theme` attribute on `<html>`, with `prefers-color-scheme` fallback. Theme persisted in `localStorage`.
- **Mobile navigation**: Pure CSS drawer using checkbox hack (no JS)
- **Galleries**: CSS Grid (2-col mobile, 3-col desktop) with GLightbox for fullscreen viewing

### JavaScript

Minimal — only two scripts inline in `default.html`:
1. **Theme toggle**: reads/writes `localStorage('theme')`, toggles `data-theme` attribute
2. **GLightbox init**: `GLightbox({ selector: '.glightbox' })` with gallery grouping via `data-gallery`

### Content Pattern

Pages use YAML front matter:
```yaml
---
layout: page
title: Page Title
permalink: /url-path/
---
```

Images are in `assets/images/` (tracked in git). Videos are in `assets/videos/` (git-ignored, fetched from Nextcloud).

### Sass Migration Note

The project uses `@use` instead of `@import` (migrated from deprecated `@import`). Partials are loaded in `main.scss` via `@use` with namespaces.
