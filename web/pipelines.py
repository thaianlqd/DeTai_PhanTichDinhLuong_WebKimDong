# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import scrapy
import pymongo
import json
import os

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
import csv

class MongoDBKimDongPipeline:
    def __init__(self):
        #note 1: Kết nối đến MongoDB tren docker
        econnect = str(os.environ['Mongo_HOST']) 
        self.client = pymongo.MongoClient('mongodb://'+econnect+':27017')
        
        # #note2: ket noi voi mongo tren windows
        # self.client = pymongo.MongoClient('mongodb://localhost:27017')
        # self.db = self.client['books_data_KimDong_12']  # Tạo Database  
        # self.collection = self.db['books_KimDong']  # Định nghĩa collection ở đây 
        
        #note 3: kết nối đến MongoDB trên docker - giúp thực thi chạy nhanh hơn 
        # mongo_host = os.getenv('Mongo_HOST', 'localhost')  # Sử dụng 'localhost' nếu không có biến môi trường
        # try:
        #     # Kết nối đến MongoDB
        #     self.client = pymongo.MongoClient(f'mongodb://{mongo_host}:27017', serverSelectionTimeoutMS=5000)
        #     self.db = self.client['books_data_KimDong_12']  # Tạo Database  
        #     self.collection = self.db['books_KimDong']  # Định nghĩa collection ở đây 
            
        #     # Kiểm tra kết nối thành công
        #     self.client.admin.command('ping')
        # except pymongo.errors.ServerSelectionTimeoutError:
        #     print(f"Không thể kết nối đến MongoDB tại host: {mongo_host}")
        #     raise

    def process_item(self, item, spider):
        try:
            #note: Chèn item vào MongoDB
            self.collection.insert_one(dict(item))
        except Exception as e:
            raise DropItem(f"Error inserting item into MongoDB: {e}")
        return item

    def close_spider(self, spider):
        self.client.close()

class JsonDBKimDongPipeline:
    def __init__(self):
        #note: Mở file JSON để ghi
        self.file = open('data_books.json', 'w', encoding='utf-8-sig')

    def process_item(self, item, spider):
        try:
            #note: Ghi item vào file JSON
            line = json.dumps(dict(item), ensure_ascii=False) + '\n'
            #note: chuyển item thành 1 dictionary, ensure_ascii => đảm bảo json theo dạng utf-8 chứ k theo kiểu ascii
            self.file.write(line)
        except Exception as e:
            raise DropItem(f"Error saving item to JSON: {e}")
        return item

    def close_spider(self, spider):
        self.file.close()

class CSVDWebKimDongPipeline:
    def __init__(self):
        # Mở file CSV để ghi
        self.file = open('data_books.csv', 'w', newline='', encoding='utf-8-sig')
        
        # Định nghĩa writer cho CSV
        self.writer = csv.writer(self.file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        
        # Ghi tiêu đề cột vào file CSV
        self.writer.writerow([
            'Tiêu đề sách',
            'Đã bán (Sách)',
            'Giá bán (VNĐ)',
            'Giá gốc (VNĐ)',
            'Mã Kim Đồng (Mã sách)',
            'ISBN (Mã quốc tế)',
            'Tác giả',
            'Đối tượng',
            'Chiều dài (cm)',
            'Chiều rộng (cm)',
            'Số trang',
            'Định dạng',
            'Trọng lượng (gram)',
            'Bộ sách',
            'Loại sách',
            'Mô tả'
        ])

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        try:
            # Ghi dữ liệu vào file CSV
            self.writer.writerow([
                adapter.get('tieuDe', '').strip(),
                adapter.get('daBan', '').strip(),
                adapter.get('giaSale', '').strip(),
                adapter.get('giaGoc', '').strip(),
                adapter.get('maKimDong', '').strip(),
                adapter.get('ISBN', '').strip(),
                adapter.get('tacGia', '').strip(),
                adapter.get('doiTuong', '').strip(),
                adapter.get('chieuDai', '').strip(),
                adapter.get('chieuRong', '').strip(),
                adapter.get('soTrang', '').strip(),
                adapter.get('dinhDang', '').strip(),
                adapter.get('trongLuong', '').strip(),
                adapter.get('boSach', '').strip(),
                adapter.get('loaiSach', '').strip(),
                adapter.get('moTa', '').strip()
            ])
        except Exception as e:
            raise DropItem(f"Error saving item to CSV: {e}")
        
        return item

    def close_spider(self, spider):
        # Đóng file sau khi crawler kết thúc
        self.file.close()