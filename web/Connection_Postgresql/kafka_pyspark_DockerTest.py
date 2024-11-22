import os
import json
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError
from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when
from pyspark.sql.types import StringType, IntegerType, DoubleType
from time import sleep

# Cấu hình MongoDB
MONGO_HOST = os.getenv('MONGO_HOST', 'mymongodb_container')
MONGO_PORT = 27017
MONGO_DB = 'books_data_KimDong_12'
MONGO_COLLECTION = 'books_KimDong'

# Cấu hình PostgreSQL
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# Cấu hình Kafka
KAFKA_TOPIC = 'books_topic'
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka_container:9093')

# Tạo Kafka topic nếu chưa tồn tại
def create_kafka_topic_if_not_exists():
    admin_client = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    try:
        admin_client.create_topics([NewTopic(name=KAFKA_TOPIC, num_partitions=1, replication_factor=1)])
        print(f"Topic {KAFKA_TOPIC} đã được tạo.")
    except TopicAlreadyExistsError:
        print(f"Topic {KAFKA_TOPIC} đã tồn tại.")
    finally:
        admin_client.close()

# Gọi hàm tạo Kafka topic nếu chưa có
create_kafka_topic_if_not_exists()

# Khởi tạo Kafka Producer
producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Bước 1: Đọc dữ liệu từ MongoDB và gửi đến Kafka
def stream_from_mongo_to_kafka():
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    collection = client[MONGO_DB][MONGO_COLLECTION]
    
    while True:
        # Đọc dữ liệu từ MongoDB
        for document in collection.find():
            record = {key: document[key] for key in document if key != "_id"}
            try:
                # Gửi dữ liệu đến Kafka
                producer.send(KAFKA_TOPIC, value=record)
                print(f"Đã gửi dữ liệu đến Kafka: {record}")
            except KafkaError as e:
                print(f"Lỗi khi gửi dữ liệu đến Kafka: {e}")
        
        sleep(10)  # Thực hiện kiểm tra định kỳ

# Khởi động luồng dữ liệu từ MongoDB đến Kafka
stream_from_mongo_to_kafka()

# Bước 2: Spark Structured Streaming Đọc Dữ Liệu từ Kafka
spark = SparkSession.builder \
    .appName("MongoDB to Kafka to PostgreSQL") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.1,org.postgresql:postgresql:42.5.0") \
    .getOrCreate()

kafka_read_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .load()

# Xử lý dữ liệu từ Kafka
books_df = kafka_read_df.selectExpr("CAST(value AS STRING) as json_data") \
    .selectExpr("from_json(json_data, 'maKimDong STRING, tieuDe STRING, giaSale DOUBLE, giaGoc DOUBLE, boSach STRING, loaiSach STRING, ISBN STRING, soTrang INT, chieuDai DOUBLE, chieuRong DOUBLE, dinhDang STRING, daBan INT, trongLuong INT, moTa STRING, tacGia STRING') AS data") \
    .select("data.*")

# Chuyển đổi kiểu dữ liệu cho PostgreSQL
books_df = books_df.withColumn("soTrang", when(col("soTrang").isNull(), 0).otherwise(col("soTrang").cast(IntegerType()))) \
                   .withColumn("trongLuong", when(col("trongLuong").isNull(), 0).otherwise(col("trongLuong").cast(IntegerType()))) \
                   .withColumn("chieuDai", when(col("chieuDai").isNull(), 0.0).otherwise(col("chieuDai").cast(DoubleType()))) \
                   .withColumn("chieuRong", when(col("chieuRong").isNull(), 0.0).otherwise(col("chieuRong").cast(DoubleType()))) \
                   .withColumn("giaSale", col("giaSale").cast(DoubleType())) \
                   .withColumn("giaGoc", col("giaGoc").cast(DoubleType()))

# Bước 3: Ghi dữ liệu vào PostgreSQL
def write_to_postgres(batch_df, batch_id):
    # Tách dữ liệu cho từng bảng
    sach_df = batch_df.select("maKimDong", "tieuDe", "giaSale", "giaGoc", "boSach", "loaiSach", "ISBN")
    chiTiet_sach_df = batch_df.select("maKimDong", "soTrang", "chieuDai", "chieuRong", "dinhDang", "daBan", "trongLuong", "moTa")
    tacGia_df = batch_df.select("maKimDong", "tacGia").where(col("tacGia").isNotNull())

    # Ghi vào bảng `sach`
    sach_df.write \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{POSTGRES_HOST}:5432/{POSTGRES_DB}") \
        .option("dbtable", "sach") \
        .option("user", POSTGRES_USER) \
        .option("password", POSTGRES_PASSWORD) \
        .mode("append") \
        .save()

    # Ghi vào bảng `chiTiet_Sach`
    chiTiet_sach_df.write \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{POSTGRES_HOST}:5432/{POSTGRES_DB}") \
        .option("dbtable", "chiTiet_Sach") \
        .option("user", POSTGRES_USER) \
        .option("password", POSTGRES_PASSWORD) \
        .mode("append") \
        .save()

    # Ghi vào bảng `sach_tacgia`
    tacGia_df.write \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{POSTGRES_HOST}:5432/{POSTGRES_DB}") \
        .option("dbtable", "sach_tacgia") \
        .option("user", POSTGRES_USER) \
        .option("password", POSTGRES_PASSWORD) \
        .mode("append") \
        .save()

# Khởi động streaming từ Spark đến PostgreSQL
postgres_write_stream = books_df.writeStream \
    .foreachBatch(write_to_postgres) \
    .option("checkpointLocation", "/tmp/postgres_checkpoint") \
    .start()

# Chạy các luồng
postgres_write_stream.awaitTermination()
