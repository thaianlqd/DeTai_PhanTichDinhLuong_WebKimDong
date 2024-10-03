import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor
from web.items import WebBooksitem
from bs4 import BeautifulSoup
#from twisted.internet import asyncioreactor  # Thêm dòng này

class WebNXBKimDong(scrapy.Spider):
    name = 'WebNXBNhiDong_Crawler'
    allowed_domains = ['nxbkimdong.com.vn']
    start_urls = [f'https://nxbkimdong.com.vn/collections/all?sort_by=best-selling&page={i}' for i in range(1, 2)]

    def parse(self, response):
        #note: Lấy URL của sách từ trang hiện tại
        base_url = 'https://nxbkimdong.com.vn'
        book_urls = response.css('.product-item a::attr(href)').getall()
        book_urls = [url for url in book_urls if url]
        full_urls = [base_url + url for url in book_urls]
        #note: tìm đưỡng dẫn của các url trong trang hiện tại
        for i_url in full_urls:
            #note: tạo url đầy đủ từ các link con của cuốn sách, dùng urljoin để nối url sách + url gốc
            yield scrapy.Request(url= i_url, callback=self.parse_book)
            #note: gửi yêu cầu HTTP đến từng trang url của cuốn sách
        
    
    def parse_book(self, response):
        soup = BeautifulSoup(response.body, 'html.parser')
        item = WebBooksitem()
        item['tieuDe'] = response.xpath('//div[@class="header_wishlist"]/h1/text()').get(default="không có").strip()
        item['daBan'] = item['daBan'] = response.xpath('//div[@class="daban"]/text()').get(default="không có").strip().split()[-1] 
        item['giaSale'] = response.xpath('//span[@class="current-price ProductPrice"]/text()').get(default="không có").replace('₫', '').replace(',', '').strip()
        item['giaGoc'] = response.xpath('//span[contains(@class, "original-price ComparePrice")]/s/text()').get(default="không có").replace('₫', '').replace(',', '').strip()
        
        #item['maKimDong'] = response.xpath('//div[contains(@class, "field-item even") and contains(@class, "sku-number")]/text()').get(default="không có").strip() or response.xpath("//span[@class='field field-name-field-product-makimdong field-type-text field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/text()").get(default="không có") or response.xpath("//span[@class='field field-name-field-product-makimdong field-type-text field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/text()").get()
        item['maKimDong'] = (
            soup.find(class_='sku-number').get_text(strip=True) if soup.find(class_='sku-number') 
            else soup.find(class_='field-name-field-product-makimdong').find(class_='field-item even').get_text(strip=True) if soup.find(class_='field-name-field-product-makimdong') 
            else "không có"
        )
        
        item['ISBN'] = (
            # Sử dụng XPath từ Scrapy
            (response.xpath('//li[contains(., "ISBN")]//strong/text()').get(default="không có").strip() 
            if response.xpath('//li[contains(., "ISBN")]//strong/text()').get() 
            else None) or 
            # Sử dụng BeautifulSoup
            (soup.find(class_='field-name-field-product--isbn').find(class_='field-item even').get_text(strip=True) 
            if soup.find(class_='field-name-field-product--isbn') 
            else None)
            or 
            "không có"
        )

        
        item['tacGia'] = (
            # Sử dụng XPath từ Scrapy
            (response.xpath('//li[contains(text(), "Tác giả")]//a/text()').get(default="không có").strip() 
            if response.xpath('//li[contains(text(), "Tác giả")]//a/text()').get() 
            else None) or 
            # Sử dụng BeautifulSoup
            (soup.find(class_='tacgia-class').get_text(strip=True) 
            if soup.find(class_='tacgia-class') 
            else soup.find(class_='field-name-field-product-tacgia').find(class_='field-item even').get_text(strip=True) 
            if soup.find(class_='field-name-field-product-tacgia') 
            else None)
            or 
            "không có"
        )

        
        item['doiTuong'] = (
            # Sử dụng XPath từ Scrapy
            (response.xpath('//li[contains(text(), "Đối tượng")]//a/text()').get(default="không có").strip() 
            if response.xpath('//li[contains(text(), "Đối tượng")]//a/text()').get() 
            else None) or 
            # Sử dụng BeautifulSoup
            (soup.find(class_='doituong-class').get_text(strip=True) 
            if soup.find(class_='doituong-class') 
            else soup.find(class_='field-name-field-product-dotuoi').find(class_='field-item even').get_text(strip=True) 
            if soup.find(class_='field-name-field-product-dotuoi') 
            else None)
            or 
            "không có"
        )

        # item['khuonKho'] = (
        #     # Sử dụng XPath từ Scrapy
        #     (response.xpath('//li[contains(text(), "Khuôn Khổ")]/text()').get(default="không có").strip().replace("Khuôn Khổ:", "").strip() 
        #     if response.xpath('//li[contains(text(), "Khuôn Khổ")]/text()').get() 
        #     else None) or 
        #     # Sử dụng BeautifulSoup
        #     (soup.find(class_='khuonkho-class').get_text(strip=True) 
        #     if soup.find(class_='khuonkho-class') 
        #     else soup.find(class_='field-name-field-product-khuonkho').find(class_='field-item even').get_text(strip=True) 
        #     if soup.find(class_='field-name-field-product-khuonkho') 
        #     else None)
        #     or 
        #     "không có"
        # )
        
        # item['khuonKho'] = (
        #     # Sử dụng XPath từ Scrapy
        #     (response.xpath('//li[contains(text(), "Khuôn Khổ")]/text()').get(default="không có").strip().replace("Khuôn Khổ:", "").replace("cm", "").strip() 
        #     if response.xpath('//li[contains(text(), "Khuôn Khổ")]/text()').get() 
        #     else None) or 
        #     # Sử dụng BeautifulSoup
        #     (soup.find(class_='khuonkho-class').get_text(strip=True).replace("cm", "").strip() 
        #     if soup.find(class_='khuonkho-class') 
        #     else soup.find(class_='field-name-field-product-khuonkho').find(class_='field-item even').get_text(strip=True).replace("cm", "").strip() 
        #     if soup.find(class_='field-name-field-product-khuonkho') 
        #     else None)
        #     or 
        #     "không có"
        # )
        
        # Xử lý phần khuôn khổ
        khuon_kho_data = (
            response.xpath('//li[contains(text(), "Khuôn Khổ")]/text()').get(default="không có").strip().replace("Khuôn Khổ:", "").replace("cm", "").strip() 
            if response.xpath('//li[contains(text(), "Khuôn Khổ")]/text()').get() 
            else soup.find(class_='khuonkho-class').get_text(strip=True).replace("cm", "").strip() 
            if soup.find(class_='khuonkho-class') 
            else soup.find(class_='field-name-field-product-khuonkho').find(class_='field-item even').get_text(strip=True).replace("cm", "").strip() 
            if soup.find(class_='field-name-field-product-khuonkho') 
            else "không có"
        )

        # Kiểm tra và chia khuôn khổ thành chiều dài và chiều rộng
        if "x" in khuon_kho_data:
            chieu_rong, chieu_dai = khuon_kho_data.split("x")
        elif "-" in khuon_kho_data:
            chieu_rong, chieu_dai = khuon_kho_data.split("-")
        else:
            chieu_rong, chieu_dai = khuon_kho_data, None

        # Loại bỏ khoảng trắng thừa
        chieu_dai = chieu_dai.strip() if chieu_dai else None
        chieu_rong = chieu_rong.strip() if chieu_rong else None

        item['chieuDai'] = chieu_dai
        item['chieuRong'] = chieu_rong

        item['soTrang'] = (
            # Sử dụng XPath từ Scrapy
            (response.xpath('//li[contains(text(), "Số trang")]/text()').get(default="không có").strip().split(':')[-1] 
            if response.xpath('//li[contains(text(), "Số trang")]/text()').get() 
            else None) or 
            # Sử dụng BeautifulSoup
            (soup.find('li', text='Số trang').get_text(strip=True).split(':')[-1] 
            if soup.find('li', text='Số trang') 
            else soup.find(class_='field-name-field-product-sotrang').find(class_='field-item even').get_text(strip=True) 
            if soup.find(class_='field-name-field-product-sotrang') 
            else None)
            or 
            "không có"
        )

        item['dinhDang'] = (
            # Sử dụng XPath từ Scrapy
            (response.xpath('//li[contains(text(), "Định dạng")]/text()').get(default="không có").strip().split(':')[-1] 
            if response.xpath('//li[contains(text(), "Định dạng")]/text()').get() 
            else None) or 
            # Sử dụng BeautifulSoup
            (soup.find('li', text='Định dạng').get_text(strip=True).split(':')[-1] 
            if soup.find('li', text='Định dạng') 
            else soup.find(class_='field-name-field-product-loaibia').find(class_='field-item even').get_text(strip=True) 
            if soup.find(class_='field-name-field-product-loaibia') 
            else None)
            or 
            "không có"
        )

        item['trongLuong'] = (
            # Sử dụng XPath từ Scrapy
            (response.xpath('//li[contains(text(), "Trọng lượng")]/text()').get(default="không có").strip().split(':')[-1].split()[0] 
            if response.xpath('//li[contains(text(), "Trọng lượng")]/text()').get() 
            else None) or 
            # Sử dụng BeautifulSoup
            (soup.find('li', text='Trọng lượng').get_text(strip=True).split(':')[-1].replace("gram", "").strip() 
            if soup.find('li', text='Trọng lượng') 
            else soup.find(class_='field-name-field-product-trongluong').find(class_='field-item even').get_text(strip=True).replace("gram", "").strip() 
            if soup.find(class_='field-name-field-product-trongluong') 
            else None)
            or 
            "không có"
        )

        item['boSach'] = (
            # Sử dụng XPath từ Scrapy
            (response.xpath('//li[contains(text(), "Bộ sách")]/a/text()').get(default="không có").strip() 
            if response.xpath('//li[contains(text(), "Bộ sách")]/a/text()').get() 
            else None) or 
            # Sử dụng BeautifulSoup
            (soup.find(class_='bosach-class').get_text(strip=True) 
            if soup.find(class_='bosach-class') 
            else soup.find(class_='field-name-field-product-tax-bosach').find(class_='field-item even').get_text(strip=True) 
            if soup.find(class_='field-name-field-product-tax-bosach') 
            else None)
            or 
            "không có"
        )

        #item['ISBN'] = response.xpath('//li[contains(., "ISBN")]//strong/text()').get(default="không có").strip() 
        # or response.xpath("//span[@class='field field-name-field-product--isbn field-type-text field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/text()").get() 
        # or response.xpath("//div[@class='field field-name-field-product--isbn field-type-text field-label-inline clearfix']//div[@class='field-items']//div[@class='field-item even']/text()").get()
        #item['tacGia'] = response.xpath('//li[contains(text(), "Tác giả")]//a/text()').get(default="không có").strip() or response.xpath("//span[@class='field field-name-field-product-tacgia field-type-entityreference field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/a/text()").get(default="không có")
        #item['doiTuong'] = response.xpath('//li[contains(text(), "Đối tượng")]//a/text()').get(default="không có").strip() or response.xpath("//span[@class='field field-name-field-product-dotuoi field-type-taxonomy-term-reference field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/a/text()").get(default="không có")      
        #item['khuonKho'] = response.xpath('//li[contains(text(), "Khuôn Khổ")]/text()').get(default="không có").strip() or response.xpath("//span[@class='field field-name-field-product-khuonkho field-type-text field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/text()").get(default="không có")
        
        #item['soTrang'] = response.xpath('//li[contains(text(), "Số trang")]/text()').get(default="không có").split(':')[-1].strip() or response.xpath("//span[@class='field field-name-field-product-sotrang field-type-number-decimal field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/text()").get(default="không có")
        #item['dinhDang'] = response.xpath('//li[contains(text(), "Định dạng")]/text()').get(default="không có").split(':')[-1].strip() or response.xpath("//span[@class='field field-name-field-product-loaibia field-type-text field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/text()").get(default="không có")
        #item['trongLuong'] = response.xpath('//li[contains(text(), "Trọng lượng")]/text()').get(default="không có").split(':')[-1].strip().split()[0] or response.xpath("//span[@class='field field-name-field-product-trongluong field-type-number-decimal field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/text()").get(default="không có")
        #item['boSach'] = response.xpath('//li[contains(text(), "Bộ sách")]/a/text()').get(default="không có").strip() or response.xpath("//span[@class='field field-name-field-product-tax-bosach field-type-taxonomy-term-reference field-label-inline clearfix']//span[@class='field-items']//span[@class='field-item even']/a/text()").get(default="không có")
        item['loaiSach'] = response.xpath('//div[@class="breadcrumb-small"]/a[2]/text()').get(default="không có").strip()
        item['moTa'] = ' '.join(response.xpath('//*[@id="protab0"]//text()').getall()).strip()



        yield item

if __name__ == "__main__":
    settings = get_project_settings()
    runner = CrawlerRunner(settings)
    runner.crawl(WebNXBKimDong)
    reactor.run()