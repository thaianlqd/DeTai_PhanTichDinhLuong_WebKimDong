#note: bản demo đầu tiên
# FROM python:3

# WORKDIR /usr/src/app

# COPY requirements.txt ./
# RUN pip3 install --no-cache-dir -r requirements.txt

# COPY . . 

# CMD ["sh", "-c", "sleep 60 && python -m scrapy runspider web/spiders/CaoWeb.py"]

# FROM python:3

# WORKDIR /usr/src/app

# COPY requirements.txt ./
# RUN pip3 install --no-cache-dir -r requirements.txt

# COPY . . 
# COPY spiders/data_books.json ./spiders/data_books.json  

# CMD ["sh", "-c", "sleep 60 && python -m scrapy runspider web/spiders/CaoWeb.py"]

#note: ban chinh
# FROM python:3

# # Đặt thư mục làm việc
# WORKDIR /usr/src/app

# # Sao chép requirements.txt và cài đặt các gói cần thiết
# COPY requirements.txt ./

# # Sao chép toàn bộ mã nguồn vào container
# COPY . .

# # Đặt quyền thực thi cho entrypoint.sh
# RUN chmod +x entrypoint.sh

# # Đặt entrypoint cho container
# ENTRYPOINT ["sh", "entrypoint.sh"]

#note 2: dockerfile k có kafka
# FROM python:3.11

# # Đặt thư mục làm việc
# WORKDIR /usr/src/app

# # Sao chép requirements.txt và cài đặt các gói cần thiết, bao gồm cả pyspark
# COPY requirements.txt ./ 

# # Cài đặt các gói khác trong requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# # Sao chép toàn bộ mã nguồn vào container
# COPY . .

# # Sao chép tệp pyspark_Docker.py vào đúng vị trí
# # COPY web/Connection_Postgresql/pyspark_Docker.py /usr/src/app/web/Connection_Postgresql/pyspark_Docker.py

# # Đặt quyền thực thi cho entrypoint.sh
# RUN chmod +x entrypoint.sh

# # Đặt entrypoint cho container
# ENTRYPOINT ["sh", "entrypoint.sh"]


#note3: bản về phần kafka
FROM python:3.11

# Đặt thư mục làm việc
WORKDIR /usr/src/app

# Cài đặt librdkafka-dev để hỗ trợ cài đặt confluent-kafka
# RUN apt-get update && apt-get install -y librdkafka-dev

# Sao chép requirements.txt và cài đặt các gói cần thiết, bao gồm cả pyspark
COPY requirements.txt ./

# Cài đặt các gói khác trong requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Cài đặt thư viện 'six' (nếu chưa có trong requirements.txt)
RUN pip install --no-cache-dir six

# RUN pip install confluent-kafka==2.0.2

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Đặt quyền thực thi cho entrypoint.sh
RUN chmod +x entrypoint.sh

# Đặt entrypoint cho container
ENTRYPOINT ["sh", "entrypoint.sh"]






















