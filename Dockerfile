#note: ban dau tien
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


FROM python:3.11

# Đặt thư mục làm việc
WORKDIR /usr/src/app

# Sao chép requirements.txt và cài đặt các gói cần thiết, bao gồm cả pyspark
COPY requirements.txt ./ 

# Cài đặt các gói khác trong requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Sao chép tệp pyspark_Docker.py vào đúng vị trí
# COPY web/Connection_Postgresql/pyspark_Docker.py /usr/src/app/web/Connection_Postgresql/pyspark_Docker.py

# Đặt quyền thực thi cho entrypoint.sh
RUN chmod +x entrypoint.sh

# Đặt entrypoint cho container
ENTRYPOINT ["sh", "entrypoint.sh"]









# Cài đặt pyspark trực tiếp từ pip
# RUN pip install pyspark


# Cài đặt Java cho PySpark (thay bằng openjdk-17-jdk)
# RUN apt-get update && \
#     apt-get install -y openjdk-17-jdk && \
#     apt-get clean











