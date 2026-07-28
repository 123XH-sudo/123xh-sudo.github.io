source "https://rubygems.org"

# 使用 github-pages gem，与 GitHub 内置部署完全兼容
gem "github-pages", group: :jekyll_plugins

# minimal-mistakes 主题额外需要
gem "jekyll-include-cache", group: :jekyll_plugins

# Windows and JRuby does not include zoneinfo files
platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end
gem "wdm", "~> 0.1.1", :platforms => [:mingw, :x64_mingw, :mswin]
