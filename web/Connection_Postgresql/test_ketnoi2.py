import os
import psycopg2
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, from_json
from pyspark.sql.types import StringType, IntegerType, DoubleType, StructType, StructField

# Cấu hình PostgreSQL
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# Cấu hình Kafka
KAFKA_TOPIC = 'books_topic'
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka_container:29092')

# Khởi tạo SparkSession
spark = SparkSession.builder \
    .appName("KafkaToPostgres") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1,org.postgresql:postgresql:42.5.0") \
    .config("spark.sql.shuffle.partitions", "50") \
    .getOrCreate()

# Định nghĩa schema cho dữ liệu JSON từ Kafka
schema = StructType([
    StructField("maKimDong", StringType(), True),
    StructField("tieuDe", StringType(), True),
    StructField("giaSale", DoubleType(), True),
    StructField("giaGoc", DoubleType(), True),
    StructField("boSach", StringType(), True),
    StructField("loaiSach", StringType(), True),
    StructField("ISBN", StringType(), True),
    StructField("soTrang", IntegerType(), True),
    StructField("chieuDai", DoubleType(), True),
    StructField("chieuRong", DoubleType(), True),
    StructField("dinhDang", StringType(), True),
    StructField("daBan", IntegerType(), True),
    StructField("trongLuong", IntegerType(), True),
    StructField("moTa", StringType(), True),
    StructField("tacGia", StringType(), True),
    StructField("doiTuong", StringType(), True)
])

# Hàm tạo bảng trong PostgreSQL (nếu chưa tồn tại)
def create_tables():
    try:
        # Kết nối tới PostgreSQL
        conn = psycopg2.connect(
            dbname=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, host=POSTGRES_HOST, port="5432")
        cur = conn.cursor()

        # Tạo bảng `sach` với khóa chính
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sach (
                maKimDong VARCHAR(50) PRIMARY KEY,
                tieuDe VARCHAR(255),
                giaSale DOUBLE PRECISION,
                giaGoc DOUBLE PRECISION,
                boSach VARCHAR(255),
                loaiSach VARCHAR(100),
                ISBN VARCHAR(50)
            );
        """)

        # Tạo bảng `chiTiet_Sach` với khóa ngoại
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chiTiet_Sach (
                maKimDong VARCHAR(50),
                soTrang INT,
                chieuDai DOUBLE PRECISION,
                chieuRong DOUBLE PRECISION,
                dinhDang VARCHAR(100),
                daBan INT,
                trongLuong INT,
                moTa TEXT,
                doiTuong VARCHAR(100),
                PRIMARY KEY (maKimDong),
                FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong) ON DELETE CASCADE
            );
        """)

        # Tạo bảng `sach_tacgia` với khóa chính và khóa ngoại
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sach_tacgia (
                maKimDong VARCHAR(50),
                tacGia VARCHAR(255),
                PRIMARY KEY (maKimDong, tacGia),
                FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong) ON DELETE CASCADE
            );
        """)

        # Đảm bảo thay đổi được lưu
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating tables: {e}")

# Hàm xử lý dữ liệu từ Kafka và chuyển đổi thành định dạng phù hợp
def process_kafka_data():
    try:
        # Đọc dữ liệu từ Kafka và áp dụng schema
        kafka_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
            .option("subscribe", KAFKA_TOPIC) \
            .option("startingOffsets", "earliest") \
            .option("failOnDataLoss", "false") \
            .load()

        # Chuyển đổi dữ liệu Kafka từ byte thành JSON string và áp dụng schema
        books_df = kafka_df.selectExpr("CAST(value AS STRING) as json_data") \
            .select(from_json("json_data", schema).alias("data")) \
            .select("data.*")

        # Chuyển đổi kiểu dữ liệu cho PostgreSQL
        books_df = books_df.withColumn("soTrang", when(col("soTrang").isNull(), 0).otherwise(col("soTrang").cast(IntegerType()))) \
                            .withColumn("trongLuong", when(col("trongLuong").isNull(), 0).otherwise(col("trongLuong").cast(IntegerType()))) \
                            .withColumn("chieuDai", when(col("chieuDai").isNull(), 0.0).otherwise(col("chieuDai").cast(DoubleType()))) \
                            .withColumn("chieuRong", when(col("chieuRong").isNull(), 0.0).otherwise(col("chieuRong").cast(DoubleType()))) \
                            .withColumn("giaSale", col("giaSale").cast(DoubleType())) \
                            .withColumn("giaGoc", col("giaGoc").cast(DoubleType()))

        return books_df
    except Exception as e:
        print(f"Error processing Kafka data: {e}")
        return None

# Hàm để ghi dữ liệu vào PostgreSQL
def write_to_postgres(batch_df, batch_id):
    try:
        # Tách dữ liệu cho từng bảng
        sach_df = batch_df.select("maKimDong", "tieuDe", "giaSale", "giaGoc", "boSach", "loaiSach", "ISBN")
        chiTiet_sach_df = batch_df.select("maKimDong", "soTrang", "chieuDai", "chieuRong", "dinhDang", "daBan", "trongLuong", "moTa", "doiTuong")
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

    except Exception as e:
        print(f"Error writing to Postgres: {e}")

# Chạy chương trình
if __name__ == "__main__":
    # Tạo bảng PostgreSQL (nếu chưa tồn tại)
    create_tables()

    # Xử lý dữ liệu từ Kafka
    books_df = process_kafka_data()
    if books_df:
        # Khởi động streaming từ Kafka đến PostgreSQL
        postgres_write_stream = books_df.writeStream \
            .foreachBatch(write_to_postgres) \
            .option("checkpointLocation", "/tmp/postgres_checkpoint") \
            .start()

        # Chạy các luồng
        postgres_write_stream.awaitTermination()
