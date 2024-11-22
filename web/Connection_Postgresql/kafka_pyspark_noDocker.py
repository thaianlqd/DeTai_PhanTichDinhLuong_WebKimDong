from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, trim
import psycopg2
from confluent_kafka import Producer
import json

# Kết nối tới PostgreSQL
def connect_to_postgres():
    conn = psycopg2.connect(
        dbname='myDataBase',
        user='postgres',
        password='12345',
        host='localhost',
        port='5433'
    )
    return conn

# Tạo Spark session
def create_spark_session():
    spark = SparkSession.builder \
        .appName("MongoDB to PostgreSQL") \
        .config("spark.mongodb.input.uri", "mongodb://localhost:27017/books_data_KimDong_20.books_KimDong") \
        .config("spark.jars", "/path/to/postgresql-42.2.20.jar") \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1") \
        .getOrCreate()
    return spark

# Tạo các bảng trong PostgreSQL
def create_tables(conn):
    with conn.cursor() as cursor:
        cursor.execute('''CREATE TABLE IF NOT EXISTS sach (
            maKimDong VARCHAR(255) PRIMARY KEY,
            tieu_de VARCHAR(255),
            gia_ban NUMERIC,
            gia_goc NUMERIC,
            ten_bo_sach VARCHAR(100),
            ten_loai_sach VARCHAR(100),
            isbn VARCHAR(50)
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS sach_tacgia (
            maKimDong VARCHAR(255),
            ten_tac_gia VARCHAR(255),
            PRIMARY KEY (maKimDong, ten_tac_gia),
            CONSTRAINT fk_sach FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS chiTiet_Sach (
            maKimDong VARCHAR(255) PRIMARY KEY,
            so_trang INT,
            chieu_rong NUMERIC,
            chieu_dai NUMERIC,
            dinh_dang VARCHAR(50),
            mo_ta TEXT,
            da_ban INT,
            trong_luong INT,
            doi_tuong VARCHAR(100),
            CONSTRAINT fk_sach FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
        )''')

        conn.commit()

# Khởi tạo Kafka Producer
def create_kafka_producer():
    conf = {
        'bootstrap.servers': 'localhost:9092',  # Đảm bảo bạn sử dụng đúng cấu hình
        'client.id': 'client-1'
    }
    producer = Producer(conf)
    return producer

# Ghi dữ liệu vào Kafka
def write_data_to_kafka(producer, book_data):
    try:
        # Chuyển đổi dict thành chuỗi JSON
        json_data = json.dumps(book_data)
        # Ghi chuỗi JSON vào Kafka
        producer.produce('books_topic', value=json_data.encode('utf-8'))  # 'books_topic' là tên topic bạn muốn sử dụng
        producer.flush()  # Đảm bảo dữ liệu được gửi ngay lập tức
    except Exception as e:
        print(f"Error writing to Kafka: {e}")

# Chèn dữ liệu vào PostgreSQL
def insert_data_to_postgres(conn, book_data):
    with conn.cursor() as cursor:
        try:
            cursor.execute('''   
                INSERT INTO sach (maKimDong, tieu_de, gia_ban, gia_goc, ten_bo_sach, ten_loai_sach, isbn)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                book_data['maKimDong'],
                book_data['tieu_de'],
                book_data['gia_ban'],
                book_data['gia_goc'],
                book_data['ten_bo_sach'],
                book_data['ten_loai_sach'],
                book_data['isbn']
            ))

            cursor.execute('''INSERT INTO sach_tacgia (maKimDong, ten_tac_gia) VALUES (%s, %s)''', (
                book_data['maKimDong'],
                book_data['ten_tac_gia']
            ))

            # Xử lý giá trị chi tiết sách
            so_trang = int(book_data['so_trang']) if book_data['so_trang'] else 0
            trong_luong = int(book_data['trong_luong'].replace('.', '')) if isinstance(book_data['trong_luong'], str) else int(book_data['trong_luong'] or 0)
            chieu_dai = float(book_data['chieu_dai'].replace('.', '')) if isinstance(book_data['chieu_dai'], str) else float(book_data['chieu_dai'] or 0)
            chieu_rong = float(book_data['chieu_rong'].replace('.', '')) if isinstance(book_data['chieu_rong'], str) else float(book_data['chieu_rong'] or 0)

            cursor.execute('''INSERT INTO chiTiet_Sach (maKimDong, so_trang, chieu_rong, chieu_dai, dinh_dang, mo_ta, da_ban, trong_luong, doi_tuong)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', (
                book_data['maKimDong'],
                so_trang,
                chieu_rong,
                chieu_dai,
                book_data['dinh_dang'],
                book_data['mo_ta'],
                book_data['da_ban'],
                trong_luong,
                book_data['doi_tuong']
            ))

            conn.commit()

        except Exception as e:
            print("Error inserting data:", e)

# Load data từ MongoDB và chuyển đổi dữ liệu
def load_data_from_mongodb(spark):
    try:
        df = spark.read.format("mongo").load()
        if df.isEmpty():
            print("DataFrame is empty!")
            return None

        df.printSchema()

        # Làm sạch và chuyển đổi dữ liệu
        df = df.withColumn("soTrang", when(trim(col("soTrang")).isNotNull(), trim(col("soTrang")).cast("int")).otherwise(0))
        df = df.withColumn("trongLuong", when(trim(col("trongLuong")).isNotNull(), trim(col("trongLuong")).cast("int")).otherwise(0))
        df = df.withColumn("chieuDai", when(trim(col("chieuDai")).isNotNull(), trim(col("chieuDai")).cast("float")).otherwise(0.0))
        df = df.withColumn("chieuRong", when(trim(col("chieuRong")).isNotNull(), trim(col("chieuRong")).cast("float")).otherwise(0.0))

        return df

    except Exception as e:
        print(f"Error loading data: {e}")
        return None

# Ghi dữ liệu vào PostgreSQL
def write_to_postgres(df, conn, producer):
    # Chuyển đổi từng hàng thành dict và ghi vào PostgreSQL và Kafka
    for row in df.collect():
        book_data = {
            'tieu_de': row['tieuDe'],
            'da_ban': row['daBan'],
            'gia_ban': row['giaSale'],
            'gia_goc': row['giaGoc'],
            'maKimDong': row['maKimDong'],
            'isbn': row['ISBN'],
            'so_trang': row['soTrang'],
            'chieu_dai': row['chieuDai'],
            'chieu_rong': row['chieuRong'],
            'trong_luong': row['trongLuong'],
            'dinh_dang': row['dinhDang'],
            'mo_ta': row['moTa'],
            'doi_tuong': row['doiTuong'],
            'ten_bo_sach': row['boSach'],
            'ten_loai_sach': row['loaiSach'],
            'ten_tac_gia': row['tacGia']
        }
        insert_data_to_postgres(conn, book_data)
        write_data_to_kafka(producer, book_data)

# Hàm chính để thực hiện toàn bộ quy trình
def transfer_data_from_mongodb_to_postgres():
    spark = create_spark_session()
    conn = connect_to_postgres()
    create_tables(conn)
    producer = create_kafka_producer()

    df = load_data_from_mongodb(spark)
    if df:
        write_to_postgres(df, conn, producer)

    # Dừng Spark session và PostgreSQL connection
    conn.close()
    spark.stop()

# Chạy hàm chính
if __name__ == '__main__':
    transfer_data_from_mongodb_to_postgres()
