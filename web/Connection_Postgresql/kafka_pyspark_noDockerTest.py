from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, trim
import psycopg2
from confluent_kafka import Producer, Consumer
import json
import time

# Kết nối tới PostgreSQL
def connect_to_postgres():
    try:
        conn = psycopg2.connect(
            dbname='myDataBase',
            user='postgres',
            password='12345',
            host='localhost',
            port='5433'
        )
        return conn
    except Exception as e:
        print(f"Lỗi khi kết nối PostgreSQL: {e}")
        return None

# Tạo Spark session
def create_spark_session():
    spark = SparkSession.builder \
        .appName("MongoDB to Kafka to PostgreSQL") \
        .config("spark.mongodb.input.uri", "mongodb://localhost:27017/books_data_KimDong_20.books_KimDong") \
        .config("spark.jars", "/path/to/postgresql-42.2.20.jar") \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1") \
        .getOrCreate()
    return spark

# Khởi tạo Kafka Producer
def create_kafka_producer():
    conf = {
        'bootstrap.servers': 'localhost:9092',
        'client.id': 'client-1'
    }
    producer = Producer(conf)
    return producer

# Đẩy dữ liệu từ MongoDB vào Kafka
def push_data_to_kafka(spark, producer):
    try:
        df = spark.read.format("mongo").load()
        if df.isEmpty():
            print("DataFrame is empty!")
            return
        
        df = df.withColumn("soTrang", when(trim(col("soTrang")).isNotNull(), trim(col("soTrang")).cast("int")).otherwise(0))
        df = df.withColumn("trongLuong", when(trim(col("trongLuong")).isNotNull(), trim(col("trongLuong")).cast("int")).otherwise(0))
        df = df.withColumn("chieuDai", when(trim(col("chieuDai")).isNotNull(), trim(col("chieuDai")).cast("float")).otherwise(0.0))
        df = df.withColumn("chieuRong", when(trim(col("chieuRong")).isNotNull(), trim(col("chieuRong")).cast("float")).otherwise(0.0))

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
            producer.produce('books_topic', value=json.dumps(book_data).encode('utf-8'))
            producer.flush()
            print("Đã đẩy dữ liệu vào Kafka:", book_data)

        producer.close()  # Đóng Kafka producer

    except Exception as e:
        print(f"Lỗi khi đẩy dữ liệu vào Kafka: {e}")


# Tạo các bảng trong PostgreSQL
def create_tables(conn):
    try:
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
            print("Đã tạo bảng thành công trong PostgreSQL")

    except Exception as e:
        print(f"Lỗi khi tạo bảng trong PostgreSQL: {e}")

# Khởi tạo Kafka Consumer
def create_kafka_consumer():
    conf = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'consumer-group-1',
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    consumer.subscribe(['books_topic'])
    return consumer

# Ghi dữ liệu từ Kafka vào PostgreSQL
def write_from_kafka_to_postgres(consumer, conn):
    try:
        with conn.cursor() as cursor:
            while True:
                msg = consumer.poll(1.0)  # Thời gian chờ đợi nhận thông điệp
                if msg is None:
                    continue
                if msg.error():
                    print("Lỗi Kafka:", msg.error())
                    continue

                book_data = json.loads(msg.value().decode('utf-8'))
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

                    cursor.execute('''INSERT INTO chiTiet_Sach (maKimDong, so_trang, chieu_rong, chieu_dai, dinh_dang, mo_ta, da_ban, trong_luong, doi_tuong)
                                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', (
                        book_data['maKimDong'],
                        book_data['so_trang'],
                        book_data['chieu_rong'],
                        book_data['chieu_dai'],
                        book_data['dinh_dang'],
                        book_data['mo_ta'],
                        book_data['da_ban'],
                        book_data['trong_luong'],
                        book_data['doi_tuong']
                    ))

                    conn.commit()
                    print("Đã chèn dữ liệu thành công vào PostgreSQL:", book_data)

                except Exception as e:
                    print(f"Lỗi khi chèn dữ liệu vào PostgreSQL: {e}")

    except Exception as e:
        print(f"Lỗi khi đọc từ Kafka: {e}")

# Hàm chính để thực hiện toàn bộ quy trình
def transfer_data_from_mongodb_to_postgres():
    spark = create_spark_session()
    conn = connect_to_postgres()
    if not conn:
        return  # Nếu không thể kết nối PostgreSQL thì dừng quy trình

    create_tables(conn)
    producer = create_kafka_producer()
    consumer = create_kafka_consumer()

    push_data_to_kafka(spark, producer)  # Đẩy dữ liệu từ MongoDB vào Kafka
    write_from_kafka_to_postgres(consumer, conn)  # Đẩy dữ liệu từ Kafka vào PostgreSQL

    # Đóng các kết nối
    conn.close()
    spark.stop()
    consumer.close()  # Đảm bảo consumer được đóng đúng cách

# Chạy hàm chính
if __name__ == '__main__':
    transfer_data_from_mongodb_to_postgres()
