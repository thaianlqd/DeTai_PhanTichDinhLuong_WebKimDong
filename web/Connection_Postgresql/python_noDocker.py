import psycopg2
import json
import os
import pymongo

# Kết nối tới MongoDB
def connect_to_mongodb():
    mongo_client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = mongo_client['books_data_KimDong_182']  # Thay tên database MongoDB của bạn
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

# Tạo các bảng trong PostgreSQL dựa trên cấu trúc dữ liệu từ MongoDB
def create_tables(conn):
    with conn.cursor() as cursor:
        # Tạo bảng bosach
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bosach (
                ten_bo_sach VARCHAR(100) PRIMARY KEY
            )
        ''')

        # Tạo bảng loaisach
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loaisach (
                ten_loai_sach VARCHAR(100) PRIMARY KEY
            )
        ''')

        # Tạo bảng books (sách)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                ma_KimDong VARCHAR(50) PRIMARY KEY,
                tieu_de VARCHAR(255),
                da_ban INT,
                gia_ban NUMERIC,
                gia_goc NUMERIC,
                isbn VARCHAR(50),
                so_trang INT,
                chieu_dai NUMERIC,
                chieu_rong NUMERIC,
                trong_luong INT,
                dinh_dang VARCHAR(50),
                mo_ta TEXT,
                doi_tuong VARCHAR(100),
                ten_bo_sach VARCHAR(100),
                ten_loai_sach VARCHAR(100),
                CONSTRAINT fk_bo_sach FOREIGN KEY (ten_bo_sach) REFERENCES bosach(ten_bo_sach),
                CONSTRAINT fk_loai_sach FOREIGN KEY (ten_loai_sach) REFERENCES loaisach(ten_loai_sach)
            )
        ''')

        # Tạo bảng tác giả (liên kết với bảng books qua bảng trung gian)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tacgia (
                ten_tac_gia VARCHAR(255) PRIMARY KEY
            )
        ''')

        # Tạo bảng trung gian book_tacgia (liên kết nhiều-nhiều giữa books và tác giả)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_tacgia (
                ma_KimDong VARCHAR(50),
                ten_tac_gia VARCHAR(255),
                PRIMARY KEY (ma_KimDong, ten_tac_gia),
                CONSTRAINT ma_KimDong FOREIGN KEY (ma_KimDong) REFERENCES books(ma_KimDong),
                CONSTRAINT fk_tac_gia FOREIGN KEY (ten_tac_gia) REFERENCES tacgia(ten_tac_gia)
            )
        ''')

        conn.commit()


# Chèn dữ liệu vào PostgreSQL từ MongoDB
# Chèn dữ liệu vào PostgreSQL từ MongoDB
# Chèn dữ liệu vào PostgreSQL từ MongoDB
def insert_data_to_postgres(conn, book_data):
    with conn.cursor() as cursor:
        try:
            # Loại bỏ trường _id nếu có
            book_data.pop('_id', None)

            # In book_data ra để kiểm tra dữ liệu
            print("Đang xử lý sách:", json.dumps(book_data, ensure_ascii=False))

            # Thêm bộ sách vào bảng bosach nếu chưa tồn tại
            cursor.execute(''' 
                INSERT INTO bosach (ten_bo_sach)
                VALUES (%s)
                ON CONFLICT (ten_bo_sach) DO NOTHING
            ''', (book_data.get('boSach', '').strip(),))

            # Thêm loại sách vào bảng loaisach nếu chưa tồn tại
            cursor.execute(''' 
                INSERT INTO loaisach (ten_loai_sach)
                VALUES (%s)
                ON CONFLICT (ten_loai_sach) DO NOTHING
            ''', (book_data.get('loaiSach', '').strip(),))

            # Thêm tác giả vào bảng tacgia nếu chưa tồn tại
            cursor.execute(''' 
                INSERT INTO tacgia (ten_tac_gia)
                VALUES (%s)
                ON CONFLICT (ten_tac_gia) DO NOTHING
            ''', (book_data.get('tacGia', '').strip(),))

            # Xử lý dữ liệu cho số trang và trọng lượng
            so_trang = int(book_data.get('soTrang', '0').strip()) if book_data.get('soTrang', '0').strip().isdigit() else 0
            trong_luong = int(book_data.get('trongLuong', '0').replace('.', '').strip()) if book_data.get('trongLuong', '0').replace('.', '').isdigit() else 0

            # Xử lý dữ liệu chiều dài và chiều rộng
            chieu_dai = float(book_data.get('chieuDai', '0').strip()) if book_data.get('chieuDai', '0').strip().replace('.', '').isdigit() else 0
            chieu_rong = float(book_data.get('chieuRong', '0').strip()) if book_data.get('chieuRong', '0').strip().replace('.', '').isdigit() else 0

            # Chèn sách vào bảng books
            cursor.execute(''' 
                INSERT INTO books (ma_KimDong, tieu_de, da_ban, gia_ban, gia_goc, isbn, so_trang, chieu_dai, chieu_rong,
                                trong_luong, dinh_dang, mo_ta, doi_tuong, ten_bo_sach, ten_loai_sach)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                book_data.get('maKimDong', '').strip(),  # Để là chuỗi
                book_data.get('tieuDe', '').strip(),
                int(book_data.get('daBan', '0').strip()),
                float(book_data.get('giaSale', '0').replace(',', '').strip()),
                float(book_data.get('giaGoc', '0').replace(',', '').strip()),
                book_data.get('ISBN', '').strip(),
                so_trang,
                chieu_dai,
                chieu_rong,
                trong_luong,
                book_data.get('dinhDang', '').strip(),
                book_data.get('moTa', '').strip(),
                book_data.get('doiTuong', '').strip(),
                book_data.get('boSach', '').strip(),
                book_data.get('loaiSach', '').strip()
            ))

            # Thêm vào bảng trung gian book_tacgia
            cursor.execute(''' 
                INSERT INTO book_tacgia (ma_KimDong, ten_tac_gia)
                VALUES (%s, %s)
                ON CONFLICT (ma_KimDong, ten_tac_gia) DO NOTHING
            ''', (book_data.get('maKimDong', '').strip(), book_data.get('tacGia', '').strip()))

            conn.commit()

        except Exception as e:
            # In ra lỗi và rollback transaction
            conn.rollback()
            print(f"Error inserting data for book: {book_data.get('tieuDe', '')}. Error: {e}")
        else:
            print(f"Inserted data for book: {book_data.get('tieuDe', '')} successfully!")





# Chuyển dữ liệu từ MongoDB sang PostgreSQL
def transfer_data_from_mongodb_to_postgres():
    # Kết nối tới MongoDB
    collection = connect_to_mongodb()

    # Kết nối tới PostgreSQL
    connection = connect_to_postgres()

    # Tạo bảng trong PostgreSQL
    create_tables(connection)

    # Lấy và chèn dữ liệu từ MongoDB sang PostgreSQL
    for book_data in collection.find():
        insert_data_to_postgres(connection, book_data)

    connection.close()

if __name__ == '__main__':
    # Thực hiện chuyển dữ liệu từ MongoDB sang PostgreSQL
    transfer_data_from_mongodb_to_postgres()
    print("Đẩy dữ liệu lên postgresql thành công!!!")
