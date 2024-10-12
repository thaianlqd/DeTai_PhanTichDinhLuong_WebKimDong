import os
import psycopg2
import pymongo
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when
import json  # Thêm dòng này để import thư viện json

# PostgreSQL Connection
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# MongoDB Connection
MONGO_HOST = os.getenv('MONGO_HOST', 'mymongodb_container')
MONGO_PORT = 27017
MONGO_DB = 'books_data_KimDong_224'
MONGO_COLLECTION = 'books_KimDong'

# Tạo Spark session
def create_spark_session():
    spark = SparkSession.builder \
        .appName("MongoDB to PostgreSQL") \
        .config("spark.mongodb.input.uri", f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}.{MONGO_COLLECTION}") \
        .config("spark.jars", "/path/to/postgresql-42.2.20.jar") \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1") \
        .getOrCreate()
    return spark

#test:
# def create_spark_session():
#     spark = SparkSession.builder \
#         .appName("MongoDB to PostgreSQL") \
#         .config("spark.mongodb.input.uri", f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}.{MONGO_COLLECTION}") \
#         .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1,org.postgresql:postgresql:42.5.0") \
#         .getOrCreate()
#     return spark


def connect_to_postgres():
    """Kết nối tới PostgreSQL"""
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        port=5432
    )
    return conn

def connect_to_mongo():
    """Kết nối tới MongoDB"""
    client = pymongo.MongoClient(f'mongodb://{MONGO_HOST}:{MONGO_PORT}')
    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]
    return collection

#test:
def test_connections():
    try:
        # Kiểm tra kết nối PostgreSQL
        postgres_conn = connect_to_postgres()
        print("Connected to PostgreSQL successfully!")
        postgres_conn.close()
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")

    try:
        # Kiểm tra kết nối MongoDB
        mongo_collection = connect_to_mongo()
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")

def create_tables(conn):
    with conn.cursor() as cursor:
        # Tạo bảng sách
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sach (
                maKimDong VARCHAR(255) PRIMARY KEY,  -- Thay ma_sach thành maKimDong
                tieu_de VARCHAR(255),
                gia_ban NUMERIC,
                gia_goc NUMERIC,
                ten_bo_sach VARCHAR(100),
                ten_loai_sach VARCHAR(100),
                ten_tac_gia VARCHAR(255),  -- Không phải khóa ngoại
                isbn VARCHAR(50)
            )
        ''')

        # Tạo bảng sách_tác giả
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sach_tacgia (
                maKimDong VARCHAR(255),  -- Thay ma_sach thành maKimDong
                ten_tac_gia VARCHAR(255),
                PRIMARY KEY (maKimDong, ten_tac_gia),
                CONSTRAINT fk_sach FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)  -- Khóa ngoại
            )
        ''')

        # Tạo bảng chi tiết sách
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chiTiet_Sach (
                maKimDong VARCHAR(255) PRIMARY KEY,  -- Thay ma_sach thành maKimDong
                so_trang INT,
                chieu_rong NUMERIC,
                chieu_dai NUMERIC,
                dinh_dang VARCHAR(50),
                da_ban INT,
                trong_luong INT,
                doi_tuong VARCHAR(100),
                mo_ta TEXT,
                CONSTRAINT fk_sach FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
            )
        ''')

        conn.commit()

def remove_id_field(books_data):
    """Loại bỏ trường `_id` từ dữ liệu MongoDB"""
    for book in books_data:
        if '_id' in book:
            del book['_id']
    return books_data

def process_data_with_pyspark(books_data):
    """Xử lý dữ liệu MongoDB với PySpark"""
    spark = create_spark_session()
    
    # Loại bỏ `_id` khỏi dữ liệu trước khi chuyển vào PySpark
    books_data = remove_id_field(books_data)
    
    # Tạo DataFrame từ dữ liệu MongoDB
    books_df = spark.createDataFrame(books_data)

    # Xử lý các cột cần thiết với PySpark (ví dụ: thay thế giá trị null, chuyển đổi kiểu dữ liệu)
    books_df = books_df.withColumn("soTrang", when(col("soTrang").cast("int").isNull(), 0).otherwise(col("soTrang").cast("int"))) \
                       .withColumn("trongLuong", when(col("trongLuong").cast("int").isNull(), 0).otherwise(col("trongLuong").cast("int"))) \
                       .withColumn("chieuDai", when(col("chieuDai").cast("double").isNull(), 0).otherwise(col("chieuDai").cast("double"))) \
                       .withColumn("chieuRong", when(col("chieuRong").cast("double").isNull(), 0).otherwise(col("chieuRong").cast("double")))

    return books_df.collect()

def insert_data_to_postgres(conn, book_data):
    with conn.cursor() as cursor:
        try:
            maKimDong = book_data['maKimDong'].strip() if book_data['maKimDong'] else ''
            tieuDe = book_data['tieuDe'].strip() if book_data['tieuDe'] else ''
            boSach = book_data['boSach'].strip() if book_data['boSach'] else ''
            loaiSach = book_data['loaiSach'].strip() if book_data['loaiSach'] else ''
            tacGia = book_data['tacGia'].strip() if 'tacGia' in book_data and book_data['tacGia'] else ''
            giaSale = float(book_data['giaSale'].replace(',', '')) if isinstance(book_data['giaSale'], str) else float(book_data['giaSale'] or 0)
            giaGoc = float(book_data['giaGoc'].replace(',', '')) if isinstance(book_data['giaGoc'], str) else float(book_data['giaGoc'] or 0)

            soTrang = int(book_data['soTrang']) if book_data['soTrang'] else 0
            trongLuong = int(book_data['trongLuong'].replace('.', '')) if isinstance(book_data['trongLuong'], str) else int(book_data['trongLuong'] or 0)
            chieuDai = float(book_data['chieuDai'].replace('.', '')) if isinstance(book_data['chieuDai'], str) else float(book_data['chieuDai'] or 0)
            chieuRong = float(book_data['chieuRong'].replace('.', '')) if isinstance(book_data['chieuRong'], str) else float(book_data['chieuRong'] or 0)

            # Chèn vào bảng sach
            cursor.execute(''' 
                INSERT INTO sach (maKimDong, tieu_de, gia_ban, gia_goc, ten_bo_sach, ten_loai_sach, ten_tac_gia, isbn)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (maKimDong, tieuDe, giaSale, giaGoc, boSach, loaiSach, tacGia, book_data['ISBN'].strip()))

            # Chèn vào bảng chiTiet_Sach
            cursor.execute(''' 
                INSERT INTO chiTiet_Sach (maKimDong, so_trang, chieu_dai, chieu_rong, dinh_dang, da_ban, trong_luong, mo_ta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (maKimDong, soTrang, chieuDai, chieuRong, book_data['dinhDang'].strip(), int(book_data['daBan'].strip()) if isinstance(book_data['daBan'], str) else int(book_data['daBan'] or 0), trongLuong, book_data['moTa'].strip()))
            
            if tacGia:  # Kiểm tra nếu tacGia không rỗng
                cursor.execute('''
                    INSERT INTO sach_tacgia (makimdong, ten_tac_gia)
                    VALUES (%s, %s)
                ''', (maKimDong, tacGia))

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"Error inserting data for book: {tieuDe}. Error: {e}")
        else:
            print(f"Inserted data for book: {tieuDe} successfully!")
            
            
#test:
def read_data_from_mongo(spark):
    books_data = spark.read \
        .format("mongo") \
        .option("uri", f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}.{MONGO_COLLECTION}") \
        .load()
    
    books_data.show()  # Kiểm tra xem dữ liệu có được tải thành công không
    return books_data


def main():
    conn = connect_to_postgres()
    create_tables(conn)
    
    mongo_collection = connect_to_mongo()
    books_data = mongo_collection.find()

    books_processed = process_data_with_pyspark(list(books_data))

    for book_data in books_processed:
        insert_data_to_postgres(conn, book_data)
    
    conn.close()

if __name__ == "__main__":
    main()
