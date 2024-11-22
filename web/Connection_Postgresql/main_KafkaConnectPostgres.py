#note: file này là file làm ra - siêu quan trọng :))
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
import psycopg2

# Cấu hình PostgreSQL từ biến môi trường
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')  # Đảm bảo container PostgreSQL đúng
POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# Kiểm tra kết nối đến PostgreSQL trước
def check_postgres_connection():
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=5432  # Đảm bảo cổng phù hợp
        )
        cursor = conn.cursor()
        print("Kết nối thành công đến PostgreSQL")
        conn.close()
    except Exception as e:
        print("Không thể kết nối đến PostgreSQL:", str(e))

# Kiểm tra kết nối
check_postgres_connection()

# Tạo Spark session
spark = SparkSession.builder \
    .appName("KafkaToPostgreSQL") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.postgresql:postgresql:42.3.1") \
    .getOrCreate()

# Thiết lập mức độ log
spark.sparkContext.setLogLevel("ERROR")

# Cấu hình Kafka Stream
kafka_stream = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "kafka_container:29092") \
    .option("subscribe", "books_topic") \
    .option("startingOffsets", "earliest") \
    .load()

# Chuyển đổi dữ liệu từ Kafka (chỉ lấy cột value và chuyển từ bytes sang string)
kafka_data = kafka_stream.selectExpr("CAST(value AS STRING)")

# Định nghĩa schema cho dữ liệu JSON
json_schema = StructType([
    StructField("tieuDe", StringType(), True),
    StructField("tacGia", StringType(), True),
    StructField("daBan", StringType(), True),
    StructField("giaSale", StringType(), True),
    StructField("giaGoc", StringType(), True),
    StructField("maKimDong", StringType(), True),
    StructField("ISBN", StringType(), True),
    StructField("doiTuong", StringType(), True),
    StructField("chieuDai", StringType(), True),
    StructField("chieuRong", StringType(), True),
    StructField("soTrang", StringType(), True),
    StructField("dinhDang", StringType(), True),
    StructField("trongLuong", StringType(), True),
    StructField("boSach", StringType(), True),
    StructField("loaiSach", StringType(), True),
    StructField("moTa", StringType(), True),
])

# Parse JSON data từ cột value
parsed_data = kafka_data.select(from_json(col("value"), json_schema).alias("data"))
parsed_data = parsed_data.select("data.*")

from pyspark.sql.functions import when

# Ép kiểu dữ liệu
parsed_data = parsed_data.withColumn("daBan", col("daBan").cast(IntegerType())) \
                         .withColumn("giaSale", col("giaSale").cast(DoubleType())) \
                         .withColumn("giaGoc", col("giaGoc").cast(DoubleType())) \
                         .withColumn("chieuDai", when(col("chieuDai").isNull(), 0).otherwise(col("chieuDai").cast(DoubleType()))) \
                         .withColumn("chieuRong", when(col("chieuRong").isNull(), 0).otherwise(col("chieuRong").cast(DoubleType()))) \
                         .withColumn("soTrang", when(col("soTrang").isNull(), 0).otherwise(col("soTrang").cast(IntegerType()))) \
                         .withColumn("trongLuong", when(col("trongLuong").isNull(), 0).otherwise(col("trongLuong").cast(DoubleType())))

# Hàm tạo bảng trong PostgreSQL (nếu chưa tồn tại)
def create_table_if_not_exists():
    try:
        # Kết nối PostgreSQL để tạo bảng
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=5432
        )
        cursor = conn.cursor()

        # Tạo bảng sách
        create_books_table = '''
        CREATE TABLE IF NOT EXISTS sach (
            maKimDong VARCHAR(255) PRIMARY KEY,
            tieuDe VARCHAR(255),
            giaSale FLOAT,
            giaGoc FLOAT,
            boSach VARCHAR(255),
            loaiSach VARCHAR(255),
            ISBN VARCHAR(255)
        );
        '''
        cursor.execute(create_books_table)

        # Tạo bảng sách_tác giả
        create_authors_table = '''
        CREATE TABLE IF NOT EXISTS sach_tacgia (
            maKimDong VARCHAR(255),
            tacGia VARCHAR(255),
            PRIMARY KEY (maKimDong, tacGia),
            FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
        );
        '''
        cursor.execute(create_authors_table)

        # Tạo bảng chi tiết sách
        create_details_table = '''
        CREATE TABLE IF NOT EXISTS chitiet_sach (
            maKimDong VARCHAR(255),
            soTrang FLOAT,
            chieuRong FLOAT,
            chieuDai FLOAT,
            dinhDang VARCHAR(255),
            daBan INTEGER,
            trongLuong FLOAT,
            doiTuong VARCHAR(255),
            moTa TEXT,
            PRIMARY KEY (maKimDong),
            FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
        );
        '''
        cursor.execute(create_details_table)

        conn.commit()
        print("Các bảng đã được tạo hoặc đã tồn tại.")
        conn.close()
    except Exception as e:
        print("Lỗi khi tạo bảng:", str(e))

# Hàm ghi vào PostgreSQL
def write_to_postgres(batch_df, batch_id):
    # Đảm bảo URL PostgreSQL chính xác
    postgres_url = f"jdbc:postgresql://{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    properties = {
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "driver": "org.postgresql.Driver"
    }
    print(f"Dữ liệu trong batch (Batch ID: {batch_id}):")
    batch_df.show(truncate=False)

    # Chia dữ liệu vào các bảng tương ứng
    books_df = batch_df.select("maKimDong", "tieuDe", "giaSale", "giaGoc", "boSach", "loaiSach", "ISBN")
    authors_df = batch_df.select("maKimDong", "tacGia")
    details_df = batch_df.select("maKimDong", "soTrang", "chieuDai", "chieuRong", "dinhDang", "daBan", "trongLuong", "doiTuong", "moTa")

    # Ghi vào các bảng PostgreSQL
    books_df.write.jdbc(url=postgres_url, table="sach", mode="append", properties=properties)
    authors_df.write.jdbc(url=postgres_url, table="sach_tacgia", mode="append", properties=properties)
    details_df.write.jdbc(url=postgres_url, table="chitiet_sach", mode="append", properties=properties)

    print(f"Dữ liệu đã được ghi vào các bảng 'sach', 'sach_tacgia', và 'chitiet_sach'.")

# Tạo bảng nếu chưa tồn tại
create_table_if_not_exists()

# Ghi dữ liệu vào PostgreSQL sử dụng foreachBatch
query = parsed_data.writeStream \
    .foreachBatch(write_to_postgres) \
    .outputMode("append") \
    .start()

# Chờ cho đến khi query kết thúc
query.awaitTermination()





#note: file phòng hờ nha :v
# import os
# from pyspark.sql import SparkSession
# from pyspark.sql.functions import from_json, col
# from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
# import psycopg2

# # Cấu hình PostgreSQL từ biến môi trường
# POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')  # Đảm bảo container PostgreSQL đúng
# POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
# POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
# POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# # Kiểm tra kết nối đến PostgreSQL trước
# def check_postgres_connection():
#     try:
#         conn = psycopg2.connect(
#             host=POSTGRES_HOST,
#             database=POSTGRES_DB,
#             user=POSTGRES_USER,
#             password=POSTGRES_PASSWORD,
#             port=5432  # Đảm bảo cổng phù hợp
#         )
#         cursor = conn.cursor()
#         print("Kết nối thành công đến PostgreSQL")
#         conn.close()
#     except Exception as e:
#         print("Không thể kết nối đến PostgreSQL:", str(e))

# # Kiểm tra kết nối
# check_postgres_connection()

# # Tạo Spark session
# spark = SparkSession.builder \
#     .appName("KafkaToPostgreSQL") \
#     .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.postgresql:postgresql:42.3.1") \
#     .getOrCreate()

# # Thiết lập mức độ log
# spark.sparkContext.setLogLevel("ERROR")

# # Cấu hình Kafka Stream
# kafka_stream = spark.readStream.format("kafka") \
#     .option("kafka.bootstrap.servers", "kafka_container:29092") \
#     .option("subscribe", "books_topic") \
#     .option("startingOffsets", "earliest") \
#     .load()

# # Chuyển đổi dữ liệu từ Kafka (chỉ lấy cột value và chuyển từ bytes sang string)
# kafka_data = kafka_stream.selectExpr("CAST(value AS STRING)")


# # Định nghĩa schema cho dữ liệu JSON
# json_schema = StructType([
#     StructField("tieuDe", StringType(), True),
#     StructField("tacGia", StringType(), True),
#     StructField("daBan", StringType(), True),
#     StructField("giaSale", StringType(), True),
#     StructField("giaGoc", StringType(), True),
#     StructField("maKimDong", StringType(), True),
#     StructField("ISBN", StringType(), True),
#     StructField("doiTuong", StringType(), True),
#     StructField("chieuDai", StringType(), True),
#     StructField("chieuRong", StringType(), True),
#     StructField("soTrang", StringType(), True),
#     StructField("dinhDang", StringType(), True),
#     StructField("trongLuong", StringType(), True),
#     StructField("boSach", StringType(), True),
#     StructField("loaiSach", StringType(), True),
#     StructField("moTa", StringType(), True),
#     # Thêm các trường khác nếu cần thiết
# ])

# # Parse JSON data từ cột value
# parsed_data = kafka_data.select(from_json(col("value"), json_schema).alias("data"))
# parsed_data = parsed_data.select("data.*")

# from pyspark.sql.functions import when

# parsed_data = parsed_data.withColumn("daBan", col("daBan").cast(IntegerType())) \
#                          .withColumn("giaSale", col("giaSale").cast(DoubleType())) \
#                          .withColumn("giaGoc", col("giaGoc").cast(DoubleType())) \
#                          .withColumn("chieuDai", when(col("chieuDai").isNull(), 0).otherwise(col("chieuDai").cast(DoubleType()))) \
#                          .withColumn("chieuRong", when(col("chieuRong").isNull(), 0).otherwise(col("chieuRong").cast(DoubleType()))) \
#                          .withColumn("soTrang", when(col("soTrang").isNull(), 0).otherwise(col("soTrang").cast(IntegerType()))) \
#                          .withColumn("trongLuong", when(col("trongLuong").isNull(), 0).otherwise(col("trongLuong").cast(DoubleType())))

# # Hàm tạo bảng trong PostgreSQL (nếu chưa tồn tại)
# def create_table_if_not_exists():
#     try:
#         # Kết nối PostgreSQL để tạo bảng
#         conn = psycopg2.connect(
#             host=POSTGRES_HOST,
#             database=POSTGRES_DB,
#             user=POSTGRES_USER,
#             password=POSTGRES_PASSWORD,
#             port=5432
#         )
#         cursor = conn.cursor()
        
#         # Tạo bảng nếu chưa tồn tại
#         create_table_query = '''
#         CREATE TABLE IF NOT EXISTS books_table (
#             id SERIAL PRIMARY KEY,
#             tieuDe VARCHAR(255),
#             tacGia VARCHAR(255),
#             daBan INTEGER,
#             giaSale FLOAT,
#             giaGoc FLOAT,
#             maKimDong VARCHAR(255),
#             ISBN  VARCHAR(255),
#             doiTuong VARCHAR(255),
#             chieuDai FLOAT,
#             chieuRong FLOAT,
#             soTrang FLOAT,
#             dinhDang  VARCHAR(255),
#             trongLuong FLOAT,
#             loaiSach  VARCHAR(255),
#             boSach VARCHAR(255),
#             moTa TEXT
#         );
#         '''
#         cursor.execute(create_table_query)
#         conn.commit()
#         print("Bảng 'books_table' đã được tạo hoặc đã tồn tại.")
#         conn.close()
#     except Exception as e:
#         print("Lỗi khi tạo bảng:", str(e))

# # Hàm ghi vào PostgreSQL
# def write_to_postgres(batch_df, batch_id):
#     # Đảm bảo URL PostgreSQL chính xác
#     postgres_url = f"jdbc:postgresql://{POSTGRES_HOST}:5432/{POSTGRES_DB}"
#     properties = {
#         "user": POSTGRES_USER,
#         "password": POSTGRES_PASSWORD,
#         "driver": "org.postgresql.Driver"
#     }

#     # Kiểm tra dữ liệu trong batch
#     print(f"Dữ liệu trong batch (Batch ID: {batch_id}):")
#     batch_df.show(truncate=False)

#     # Ghi dữ liệu vào PostgreSQL
#     batch_df.write \
#         .jdbc(url=postgres_url, table="books_table", mode="append", properties=properties)
#     print(f"Dữ liệu đã được ghi vào bảng 'books_table'.")

# # Hàm hiển thị dữ liệu trong Kafka
# def show_data(batch_df, batch_id):
#     print(f"Dữ liệu Kafka trong batch (Batch ID: {batch_id}):")
#     batch_df.show(truncate=False)

# # Tạo bảng nếu chưa tồn tại
# create_table_if_not_exists()

# # Ghi dữ liệu vào PostgreSQL sử dụng foreachBatch
# query = parsed_data.writeStream \
#     .foreachBatch(write_to_postgres) \
#     .outputMode("append") \
#     .start()

# # Chờ cho đến khi query kết thúc
# query.awaitTermination()





#note: bản này chạy khá ổn nè
# import os
# from pyspark.sql import SparkSession
# from pyspark.sql.functions import from_json, col
# from pyspark.sql.types import StructType, StructField, StringType
# import psycopg2

# # Cấu hình PostgreSQL từ biến môi trường
# POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')  # Đảm bảo container PostgreSQL đúng
# POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
# POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
# POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# # Kiểm tra kết nối đến PostgreSQL trước
# def check_postgres_connection():
#     try:
#         conn = psycopg2.connect(
#             host=POSTGRES_HOST,
#             database=POSTGRES_DB,
#             user=POSTGRES_USER,
#             password=POSTGRES_PASSWORD,
#             port=5432  # Đảm bảo cổng phù hợp
#         )
#         cursor = conn.cursor()
#         print("Kết nối thành công đến PostgreSQL")
#         conn.close()
#     except Exception as e:
#         print("Không thể kết nối đến PostgreSQL:", str(e))

# # Kiểm tra kết nối
# check_postgres_connection()

# # Tạo Spark session
# spark = SparkSession.builder \
#     .appName("KafkaToPostgreSQL") \
#     .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.postgresql:postgresql:42.3.1") \
#     .getOrCreate()

# # Thiết lập mức độ log
# spark.sparkContext.setLogLevel("ERROR")

# # Cấu hình Kafka Stream
# kafka_stream = spark.readStream.format("kafka") \
#     .option("kafka.bootstrap.servers", "kafka_container:29092") \
#     .option("subscribe", "books_topic") \
#     .option("startingOffsets", "earliest") \
#     .load()


# # Chuyển đổi dữ liệu từ Kafka (chỉ lấy cột value và chuyển từ bytes sang string)
# kafka_data = kafka_stream.selectExpr("CAST(value AS STRING)")

# # Định nghĩa schema cho dữ liệu JSON
# json_schema = StructType([
#     StructField("tieuDe", StringType(), True),
#     StructField("tacGia", StringType(), True)
# ])

# # Parse JSON data từ cột value
# parsed_data = kafka_data.select(from_json(col("value"), json_schema).alias("data"))
# parsed_data = parsed_data.select("data.*")

# # Hàm tạo bảng trong PostgreSQL (nếu chưa tồn tại)
# def create_table_if_not_exists():
#     try:
#         # Kết nối PostgreSQL để tạo bảng
#         conn = psycopg2.connect(
#             host=POSTGRES_HOST,
#             database=POSTGRES_DB,
#             user=POSTGRES_USER,
#             password=POSTGRES_PASSWORD,
#             port=5432
#         )
#         cursor = conn.cursor()
        
#         # Tạo bảng nếu chưa tồn tại
#         create_table_query = '''
#         CREATE TABLE IF NOT EXISTS books_table (
#             id SERIAL PRIMARY KEY,
#             tieuDe VARCHAR(255),
#             tacGia VARCHAR(255)
#         );
#         '''
#         cursor.execute(create_table_query)
#         conn.commit()
#         print("Bảng 'books_table' đã được tạo hoặc đã tồn tại.")
#         conn.close()
#     except Exception as e:
#         print("Lỗi khi tạo bảng:", str(e))

# # Hàm ghi vào PostgreSQL
# def write_to_postgres(batch_df, batch_id):
#     # Đảm bảo URL PostgreSQL chính xác
#     postgres_url = f"jdbc:postgresql://{POSTGRES_HOST}:5432/{POSTGRES_DB}"
#     properties = {
#         "user": POSTGRES_USER,
#         "password": POSTGRES_PASSWORD,
#         "driver": "org.postgresql.Driver"
#     }

#     # Kiểm tra dữ liệu trong batch
#     print(f"Dữ liệu trong batch (Batch ID: {batch_id}):")
#     batch_df.show(truncate=False)

#     # Ghi dữ liệu vào PostgreSQL
#     batch_df.write \
#         .jdbc(url=postgres_url, table="books_table", mode="append", properties=properties)
#     print(f"Dữ liệu đã được ghi vào bảng 'books_table'.")

# # Hàm hiển thị dữ liệu trong Kafka
# def show_data(batch_df, batch_id):
#     print(f"Dữ liệu Kafka trong batch (Batch ID: {batch_id}):")
#     batch_df.show(truncate=False)

# # Tạo bảng nếu chưa tồn tại
# create_table_if_not_exists()

# # Ghi dữ liệu vào PostgreSQL sử dụng foreachBatch
# query = parsed_data.writeStream \
#     .foreachBatch(write_to_postgres) \
#     .outputMode("append") \
#     .start()

# # Chờ cho đến khi query kết thúc
# query.awaitTermination()










# from pyspark.sql import SparkSession
# from pyspark.sql.functions import expr

# # Tạo Spark session
# spark = SparkSession.builder \
#     .appName("KafkaExample") \
#     .getOrCreate()

# # Thiết lập mức độ log xuống ERROR để giảm bớt các thông báo không cần thiết
# spark.sparkContext.setLogLevel("ERROR")

# # Cấu hình kết nối đến Kafka
# kafka_stream = spark.readStream.format("kafka") \
#     .option("kafka.bootstrap.servers", "localhost:9092") \
#     .option("subscribe", "books_topic") \
#     .option("startingOffsets", "earliest") \
#     .load()


# # Chuyển đổi dữ liệu từ Kafka (chỉ lấy cột value và chuyển từ bytes sang string)
# kafka_data = kafka_stream.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

# # Hiển thị dữ liệu (ví dụ đơn giản)
# query = kafka_data \
#     .writeStream \
#     .outputMode("append") \
#     .format("console") \
#     .start()

# # Chờ cho đến khi query kết thúc
# query.awaitTermination()



