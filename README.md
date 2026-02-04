# Bartusch - Holz und Handwerk

Static website built with Jekyll. No JavaScript.

## Development

```bash
bundle install --path vendor/bundle
./scripts/download-videos.sh
bundle exec jekyll serve
```

Site runs at http://localhost:4000.

## Production

```bash
bundle install --path vendor/bundle
./scripts/download-videos.sh
bundle exec jekyll build
```

Deploy the `_site/` directory to your web server.

## Videos

Videos are stored in Nextcloud and excluded from git. The file `videos.manifest` maps local paths to Nextcloud share URLs.

To add a video:

1. Upload to Nextcloud and create a share link
2. Add a line to `videos.manifest`: `local/path.mp4<TAB>https://share-url/download`
3. Run `./scripts/download-videos.sh`

## Project Structure

```
_config.yml        # Jekyll configuration
index.md           # Homepage
_pages/            # Content pages
_layouts/          # HTML templates
_includes/         # Partials (nav, footer)
_sass/             # SCSS stylesheets
assets/            # CSS, images, videos
scripts/           # Build/deploy scripts
videos.manifest    # Video download URLs
```
