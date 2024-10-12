# #!/bin/sh
# set -e

# # Đợi một chút trước khi chạy Scrapy (tùy chọn)
# echo "Đang chờ 20 giây trước khi chạy Scrapy..."
# sleep 20

# # Chạy Scrapy để cào dữ liệu
# echo "Bắt đầu cào dữ liệu với Scrapy..."
# python -m scrapy runspider web/spiders/CaoWeb.py

# # Kiểm tra xem quá trình cào dữ liệu có thành công không
# if [ $? -eq 0 ]; then
#     echo "Cào dữ liệu thành công, bắt đầu chèn dữ liệu vào PostgreSQL."
#     # Sau khi cào xong, chạy db_connection.py để chèn dữ liệu vào PostgreSQL
#     #python web/Connection_Postgresql/pyspark_Docker.py
#     # python /usr/src/app/web/Connection_Postgresql/pyspark_Docker.py
#     spark-submit --master spark://spark_container:7077 /usr/src/app/web/Connection_Postgresql/pyspark_Docker.py

# else
#     echo "Cào dữ liệu thất bại. Không thể chèn dữ liệu vào PostgreSQL."
#     exit 1
# fi

#!/bin/sh
set -e

# Đợi 20 giây trước khi chạy Scrapy
echo "Đang chờ 20 giây trước khi chạy Scrapy..."
sleep 20

# Chạy Scrapy để cào dữ liệu
echo "Bắt đầu cào dữ liệu với Scrapy..."
python -m scrapy runspider web/spiders/CaoWeb.py

# Kiểm tra xem quá trình cào dữ liệu có thành công không
if [ $? -eq 0 ]; then
    echo "Cào dữ liệu thành công, Spark job sẽ được gửi tới spark_container."
else
    echo "Cào dữ liệu thất bại."
    exit 1
fi
