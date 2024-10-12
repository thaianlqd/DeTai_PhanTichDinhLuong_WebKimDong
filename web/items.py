# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class WebBooksitem(scrapy.Item):
    # define the fields for your item here like:
    tieuDe = scrapy.Field()
    #danhGia = scrapy.Field()
    daBan = scrapy.Field()
    giaSale = scrapy.Field()
    giaGoc = scrapy.Field()
    maKimDong = scrapy.Field()
    ISBN = scrapy.Field()
    tacGia = scrapy.Field()
    doiTuong = scrapy.Field()
    # khuonKho = scrapy.Field()
    chieuDai = scrapy.Field()
    chieuRong = scrapy.Field()
    soTrang = scrapy.Field()
    dinhDang = scrapy.Field()
    trongLuong = scrapy.Field()
    boSach = scrapy.Field()
    loaiSach = scrapy.Field()
    moTa = scrapy.Field()
    
