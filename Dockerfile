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




















