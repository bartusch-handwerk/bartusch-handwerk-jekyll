# Copy sitemap.xml to page-sitemap.xml for legacy WordPress compatibility
Jekyll::Hooks.register :site, :post_write do |site|
  sitemap_path = File.join(site.dest, 'sitemap.xml')
  legacy_path = File.join(site.dest, 'page-sitemap.xml')

  if File.exist?(sitemap_path)
    FileUtils.cp(sitemap_path, legacy_path)
  end
end
