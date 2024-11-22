from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, trim
import pymongo
import psycopg2

# Kết nối tới MongoDB bằng pymongo để lấy dữ liệu
def connect_to_mongodb():
    mongo_client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = mongo_client['books_data_KimDong_20']  # Thay tên database MongoDB của bạn
    collection = db['books_KimDong']  # Thay tên collection của bạn
    return collection

# Kết nối tới PostgreSQL (trường hợp sử dụng localhost)
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
        # Tạo bảng sách
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sach (
                maKimDong VARCHAR(255) PRIMARY KEY,  -- Thay ma_sach thành maKimDong
                tieu_de VARCHAR(255),
                gia_ban NUMERIC,
                gia_goc NUMERIC,
                ten_bo_sach VARCHAR(100),
                ten_loai_sach VARCHAR(100),
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
                mo_ta TEXT,
                da_ban INT,
                trong_luong INT,
                doi_tuong VARCHAR(100),
                CONSTRAINT fk_sach FOREIGN KEY (maKimDong) REFERENCES sach(maKimDong)
            )
        ''')

        conn.commit()




def insert_data_to_postgres(conn, book_data):
    print("Book data:", book_data)  # In dữ liệu để kiểm tra
    with conn.cursor() as cursor:
        try:
            # Chèn dữ liệu vào bảng sach
            cursor.execute('''   
                INSERT INTO sach (maKimDong, tieu_de, gia_ban, gia_goc, ten_bo_sach, ten_loai_sach, isbn)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                book_data['maKimDong'],  # Thay ma_sach thành maKimDong
                book_data['tieu_de'],  # Đảm bảo sử dụng 'tieu_de' (in thường)
                book_data['gia_ban'],
                book_data['gia_goc'],
                book_data['ten_bo_sach'],  # Đảm bảo sử dụng 'ten_bo_sach'
                book_data['ten_loai_sach'],  # Đảm bảo sử dụng 'ten_loai_sach'
                book_data['isbn']
            ))

            # Chèn dữ liệu vào bảng sach_tacgia
            cursor.execute('''
                INSERT INTO sach_tacgia (maKimDong, ten_tac_gia)
                VALUES (%s, %s)
            ''', (
                book_data['maKimDong'],  # Thay ma_sach thành maKimDong
                book_data['ten_tac_gia']  # Đảm bảo sử dụng 'ten_tac_gia'
            ))
            
            so_trang = int(book_data['so_trang']) if book_data['so_trang'] else 0
            trong_luong = int(book_data['trong_luong'].replace('.', '')) if isinstance(book_data['trong_luong'], str) else int(book_data['trong_luong'] or 0)
            chieu_dai = float(book_data['chieu_dai'].replace('.', '')) if isinstance(book_data['chieu_dai'], str) else float(book_data['chieu_dai'] or 0)
            chieu_rong = float(book_data['chieu_rong'].replace('.', '')) if isinstance(book_data['chieu_rong'], str) else float(book_data['chieu_rong'] or 0)

            # Chèn dữ liệu vào bảng chiTiet_Sach
            cursor.execute('''
                INSERT INTO chiTiet_Sach (maKimDong, so_trang, chieu_rong, chieu_dai, dinh_dang, mo_ta, da_ban, trong_luong, doi_tuong)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',  (
                book_data['maKimDong'],  # Thay ma_sach thành maKimDong
                so_trang,  # Sử dụng giá trị đã xử lý
                chieu_rong,  # Sử dụng giá trị đã xử lý
                chieu_dai,  # Sử dụng giá trị đã xử lý
                book_data['dinh_dang'],  # Đảm bảo sử dụng 'dinh_dang' (in thường)
                book_data['mo_ta'],
                book_data['da_ban'],
                trong_luong,  # Sử dụng giá trị đã xử lý
                book_data['doi_tuong']
            ))

            conn.commit()

        except Exception as e:
            print("Error inserting data:", e)



# Load data từ MongoDB và chuyển đổi dữ liệu
def load_data_from_mongodb(spark):
    spark = spark.newSession()
    spark.conf.set("spark.mongodb.input.uri", "mongodb://localhost:27017/books_data_KimDong_20.books_KimDong")

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
def write_to_postgres(df, conn):
    for row in df.collect():
        print("Row data:", row)  # In ra toàn bộ dòng dữ liệu
        book_data = {
            'tieu_de': row['tieuDe'],  # Đổi thành 'tieu_de'
            'da_ban': row['daBan'],
            'gia_ban': row['giaSale'],
            'gia_goc': row['giaGoc'],
            'maKimDong': row['maKimDong'],  # Đảm bảo rằng trường này có trong row
            'isbn': row['ISBN'],
            'so_trang': row['soTrang'],
            'chieu_dai': row['chieuDai'],  # Đổi thành 'chieu_dai'
            'chieu_rong': row['chieuRong'],  # Đổi thành 'chieu_rong'
            'trong_luong': row['trongLuong'],  # Đổi thành 'trong_luong'
            'dinh_dang': row['dinhDang'],  # Đổi thành 'dinh_dang'
            'mo_ta': row['moTa'],
            'doi_tuong': row['doiTuong'],
            'ten_bo_sach': row['boSach'],  # Đổi thành 'ten_bo_sach'
            'ten_loai_sach': row['loaiSach'],  # Đổi thành 'ten_loai_sach'
            'ten_tac_gia': row['tacGia']  # Đổi thành 'ten_tac_gia'
        }

        insert_data_to_postgres(conn, book_data)


# Main function
def transfer_data_from_mongodb_to_postgres():
    spark = create_spark_session()
    df = load_data_from_mongodb(spark)
    if df is not None:
        df.show(5)  # In ra 5 dòng đầu tiên để kiểm tra dữ liệu
        connection = connect_to_postgres()
        create_tables(connection)
        write_to_postgres(df, connection)
        connection.close()
        print("Đẩy dữ liệu lên PostgreSQL thành công!!!")
    else:
        print("Không có dữ liệu để chuyển.")

    spark.stop()

if __name__ == '__main__':
    transfer_data_from_mongodb_to_postgres()
