import os
import pymongo
import psycopg2
from kafka import KafkaProducer, KafkaConsumer
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when
import json

# MongoDB Connection
MONGO_HOST = os.getenv('MONGO_HOST', 'mymongodb_container')
MONGO_PORT = 27017
MONGO_DB = 'books_data_KimDong_10'
MONGO_COLLECTION = 'books_KimDong'

# PostgreSQL Connection
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# Kafka Configuration
KAFKA_TOPIC = 'books_topic'
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka_container:9092')

# Tạo Spark session
def create_spark_session():
    spark = SparkSession.builder \
        .appName("MongoDB to PostgreSQL") \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1,org.postgresql:postgresql:42.5.0") \
        .getOrCreate()
    return spark

def connect_to_mongo():
    """Kết nối tới MongoDB"""
    client = pymongo.MongoClient(f'mongodb://{MONGO_HOST}:{MONGO_PORT}')
    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]
    return collection

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

def create_tables(conn):
    with conn.cursor() as cursor:
        # Tạo bảng sách
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sach (
                maKimDong VARCHAR(255) PRIMARY KEY,
                tieu_de VARCHAR(255),
                gia_ban NUMERIC,
                gia_goc NUMERIC,
                ten_bo_sach VARCHAR(100),
                ten_loai_sach VARCHAR(100),
                isbn VARCHAR(50)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chiTiet_Sach (
                maKimDong VARCHAR(255) PRIMARY KEY,
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sach_tacgia (
                maKimDong VARCHAR(255),
                ten_tac_gia VARCHAR(255),
                PRIMARY KEY (maKimDong, ten_tac_gia),
                CONSTRAINT fk_sach FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
            )
        ''')
        conn.commit()

def produce_messages():
    """Đọc dữ liệu từ MongoDB và gửi từng bản ghi vào Kafka"""
    mongo_collection = connect_to_mongo()
    books_data = mongo_collection.find()

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    for book in books_data:
        if '_id' in book:
            del book['_id']  # Loại bỏ trường `_id` của MongoDB
        producer.send(KAFKA_TOPIC, book)
        print(f"Produced message: {book}")

    producer.flush()
    producer.close()

def process_and_insert_to_postgres():
    """Đọc dữ liệu từ Kafka, xử lý với PySpark và chèn vào PostgreSQL"""
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    conn = connect_to_postgres()
    create_tables(conn)

    spark = create_spark_session()

    for message in consumer:
        book_data = message.value
        books_df = spark.createDataFrame([book_data])

        # Xử lý với PySpark
        books_df = books_df.withColumn("soTrang", when(col("soTrang").cast("int").isNull(), 0).otherwise(col("soTrang").cast("int"))) \
                           .withColumn("trongLuong", when(col("trongLuong").cast("int").isNull(), 0).otherwise(col("trongLuong").cast("int"))) \
                           .withColumn("chieuDai", when(col("chieuDai").cast("double").isNull(), 0).otherwise(col("chieuDai").cast("double"))) \
                           .withColumn("chieuRong", when(col("chieuRong").cast("double").isNull(), 0).otherwise(col("chieuRong").cast("double")))

        # Chuyển dữ liệu thành dictionary để dễ chèn vào PostgreSQL
        book_data = books_df.collect()[0].asDict()

        with conn.cursor() as cursor:
            try:
                cursor.execute(''' 
                    INSERT INTO sach (maKimDong, tieu_de, gia_ban, gia_goc, ten_bo_sach, ten_loai_sach, isbn)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (book_data['maKimDong'], book_data['tieuDe'], book_data['giaSale'], book_data['giaGoc'], 
                      book_data['boSach'], book_data['loaiSach'], book_data['ISBN']))

                cursor.execute(''' 
                    INSERT INTO chiTiet_Sach (maKimDong, so_trang, chieu_dai, chieu_rong, dinh_dang, da_ban, trong_luong, mo_ta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (book_data['maKimDong'], book_data['soTrang'], book_data['chieuDai'], book_data['chieuRong'], 
                      book_data['dinhDang'], book_data['daBan'], book_data['trongLuong'], book_data['moTa']))

                if book_data['tacGia']:
                    cursor.execute('''
                        INSERT INTO sach_tacgia (makimdong, ten_tac_gia)
                        VALUES (%s, %s)
                    ''', (book_data['maKimDong'], book_data['tacGia']))

                conn.commit()
                print(f"Inserted data for book: {book_data['tieuDe']} successfully!")
            except Exception as e:
                conn.rollback()
                print(f"Error inserting data for book: {book_data['tieuDe']}. Error: {e}")

    conn.close()
    spark.stop()

if __name__ == "__main__":
    # Produce messages from MongoDB to Kafka
    produce_messages()

    # Consume messages from Kafka and insert into PostgreSQL
    process_and_insert_to_postgres()
