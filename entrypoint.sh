#note 1: bản chưa sử dụng kafka
# #!/bin/sh
# set -e

# # Đợi 20 giây trước khi chạy Scrapy
# echo "Đang chờ 20 giây trước khi chạy Scrapy..."
# sleep 20

# # Chạy Scrapy để cào dữ liệu
# echo "Bắt đầu cào dữ liệu với Scrapy..."
# python -m scrapy runspider web/spiders/CaoWeb.py

# # Kiểm tra xem quá trình cào dữ liệu có thành công không
# if [ $? -eq 0 ]; then
#     echo "Cào dữ liệu thành công, Spark job sẽ được gửi tới spark_container."
# else
#     echo "Cào dữ liệu thất bại."
#     exit 1
# fi


#note 2: bản mới sử dụng kafka 
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
    echo "Cào dữ liệu và đẩy dữ liệu lên MongoDB thành công, tiếp theo sẽ chạy Python script main_MongoDBConnectKafka.py ..."
else
    echo "Cào dữ liệu và đẩy dữ liệu lên MongoDB thất bại."
    exit 1
fi

#Chạy Python script test_ketnoi.py sau khi cào dữ liệu thành công
echo "Bắt đầu chạy Python script test_ketnoi.py..."
python web/Connection_Postgresql/main_MongoDBConnectKafka.py

# Kiểm tra xem quá trình chạy script có thành công không
if [ $? -eq 0 ]; then
    echo "Chạy script main_MongoDBConnectKafka.py và đẩy dữ liệu từ MongoDB lên Kafka thành công, Spark job sẽ được gửi tới spark_container."
else
    echo "Chạy script main_MongoDBConnectKafka.py thất bại."
    exit 1
fi


