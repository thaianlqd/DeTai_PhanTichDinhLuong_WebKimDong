# Ghi chú: File này chứa luồng xử lý dữ liệu Kafka tới PostgreSQL thông qua Spark và Airflow

# Import các thư viện cần thiết
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
import psycopg2
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime

# Cấu hình biến môi trường PostgreSQL
# Đảm bảo các biến này được thiết lập đúng trong hệ thống hoặc Docker để kết nối đến PostgreSQL
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres_container')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '12345')

# Hàm kiểm tra kết nối đến PostgreSQL
# Hàm này được dùng để xác minh rằng PostgreSQL có sẵn để sử dụng trước khi bắt đầu xử lý
def check_postgres_connection():
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=5432  # Cổng mặc định
        )
        cursor = conn.cursor()
        print("Kết nối thành công đến PostgreSQL")
        conn.close()
    except Exception as e:
        print("Không thể kết nối đến PostgreSQL:", str(e))

# Hàm tạo Spark session cho việc xử lý dữ liệu
def create_spark_session():
    return SparkSession.builder \
        .appName("KafkaToPostgreSQL") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.postgresql:postgresql:42.3.1") \
        .getOrCreate()

# Cấu hình Kafka Stream để đọc dữ liệu
def read_kafka_stream(spark):
    kafka_stream = spark.readStream.format("kafka") \
        .option("kafka.bootstrap.servers", "kafka_container:29092") \
        .option("subscribe", "books_topic") \
        .option("startingOffsets", "earliest") \
        .load()
    return kafka_stream.selectExpr("CAST(value AS STRING)")

# Định nghĩa schema JSON để chuyển đổi dữ liệu từ Kafka
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

# Hàm tạo bảng trong PostgreSQL nếu chưa tồn tại
def create_table_if_not_exists():
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=5432
        )
        cursor = conn.cursor()

        # Tạo bảng 'sach'
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

        # Tạo bảng 'sach_tacgia'
        create_authors_table = '''
        CREATE TABLE IF NOT EXISTS sach_tacgia (
            maKimDong VARCHAR(255),
            tacGia VARCHAR(255),
            PRIMARY KEY (maKimDong, tacGia),
            FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
        );
        '''
        cursor.execute(create_authors_table)

        # Tạo bảng 'chitiet_sach'
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

# Hàm ghi dữ liệu vào PostgreSQL
def write_to_postgres(batch_df, batch_id):
    postgres_url = f"jdbc:postgresql://{POSTGRES_HOST}:5432/{POSTGRES_DB}"
    properties = {
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "driver": "org.postgresql.Driver"
    }
    
    print(f"Dữ liệu trong batch (Batch ID: {batch_id}):")
    batch_df.show(truncate=False)

    books_df = batch_df.select("maKimDong", "tieuDe", "giaSale", "giaGoc", "boSach", "loaiSach", "ISBN")
    authors_df = batch_df.select("maKimDong", "tacGia")
    details_df = batch_df.select("maKimDong", "soTrang", "chieuDai", "chieuRong", "dinhDang", "daBan", "trongLuong", "doiTuong", "moTa")

    books_df.write.jdbc(url=postgres_url, table="sach", mode="append", properties=properties)
    authors_df.write.jdbc(url=postgres_url, table="sach_tacgia", mode="append", properties=properties)
    details_df.write.jdbc(url=postgres_url, table="chitiet_sach", mode="append", properties=properties)

    print(f"Dữ liệu đã được ghi vào các bảng 'sach', 'sach_tacgia', và 'chitiet_sach'.")

# Định nghĩa DAG và các tác vụ trong Airflow
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1
}

# DAG thực hiện xử lý dữ liệu Kafka tới PostgreSQL thông qua Spark
with DAG('kafka_to_postgres_pipeline', default_args=default_args, schedule_interval='@daily') as dag:

    # Kiểm tra kết nối PostgreSQL
    check_postgres = PythonOperator(
        task_id='check_postgres_connection',
        python_callable=check_postgres_connection
    )

    # Tạo bảng PostgreSQL nếu chưa có
    create_tables = PythonOperator(
        task_id='create_tables',
        python_callable=create_table_if_not_exists
    )

    # Chạy Spark job để ghi dữ liệu từ Kafka vào PostgreSQL
    run_spark_job = PythonOperator(
        task_id='run_spark_job',
        python_callable=lambda: write_to_postgres(parsed_data, batch_id)
    )

    check_postgres >> create_tables >> run_spark_job
