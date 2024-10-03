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

FROM python:3

# Đặt thư mục làm việc
WORKDIR /usr/src/app

# Sao chép requirements.txt và cài đặt các gói cần thiết
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Đặt quyền thực thi cho entrypoint.sh
RUN chmod +x entrypoint.sh

# Đặt entrypoint cho container
ENTRYPOINT ["sh", "entrypoint.sh"]






