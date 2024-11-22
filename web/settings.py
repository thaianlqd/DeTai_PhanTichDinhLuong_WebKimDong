# Scrapy settings for web project

BOT_NAME = "web"

SPIDER_MODULES = ["web.spiders"]
NEWSPIDER_MODULE = "web.spiders"

# Cấu hình nhận diện bot (nếu cần)
#USER_AGENT = "web (+http://www.yourdomain.com)"

# Tuân thủ robots.txt rules
ROBOTSTXT_OBEY = True

# Thiết lập độ trễ download (delay giữa các request)
DOWNLOAD_DELAY = 0
CONCURRENT_REQUESTS = 512

# Bật/tắt cookies
#COOKIES_ENABLED = False

# Tắt Telnet Console (tùy chọn)
#TELNETCONSOLE_ENABLED = False

# Cấu hình tiêu đề mặc định cho các request
#DEFAULT_REQUEST_HEADERS = {
#   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#   "Accept-Language": "en",
#}

# Bật/tắt middlewares của spider
#SPIDER_MIDDLEWARES = {
#    "web.middlewares.WebSpiderMiddleware": 543,
#}

# Bật/tắt downloader middlewares
#DOWNLOADER_MIDDLEWARES = {
#    "web.middlewares.WebDownloaderMiddleware": 543,
#}

# Cấu hình pipelines
ITEM_PIPELINES = {
   "web.pipelines.CSVDWebKimDongPipeline": 300,
   "web.pipelines.JsonDBKimDongPipeline": 400,
   "web.pipelines.MongoDBKimDongPipeline": 500,
}

# Bật AutoThrottle để tự động điều chỉnh tốc độ
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0
AUTOTHROTTLE_TARGET_CONCURRENCY = 10.0

# Bật cache HTTP (tùy chọn)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Đảm bảo việc sử dụng request fingerprinter và reactor mới
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
# TWISTED_REACTOR = 'twisted.internet.selectreactor.SelectReactor'

from twisted.internet import selectreactor
selectreactor.install()


# Cấu hình encoding cho xuất file
FEED_EXPORT_ENCODING = 'utf-8'
