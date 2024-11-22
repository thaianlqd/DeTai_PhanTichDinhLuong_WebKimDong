import os
import json
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaProducer, KafkaConsumer
from pymongo import MongoClient
from time import sleep
import time

# Cấu hình MongoDB
MONGO_HOST = os.getenv('MONGO_HOST', 'mymongodb_container')
MONGO_PORT = 27017
MONGO_DB = 'books_data_KimDong_12'
MONGO_COLLECTION = 'books_KimDong'

# Cấu hình Kafka
KAFKA_TOPIC = 'books_topic'
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka_container:29092')

# Khởi tạo Kafka Admin Client để kiểm tra và tạo topic nếu cần
admin_client = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

# Hàm để tạo topic nếu chưa tồn tại
def create_topic_if_not_exists(topic_name):
    try:
        topics = admin_client.list_topics()
        if topic_name not in topics:
            print(f"Topic {topic_name} chưa tồn tại, đang tạo mới...")
            new_topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
            admin_client.create_topics(new_topics=[new_topic], validate_only=False)
            print(f"Topic {topic_name} đã được tạo.")
        else:
            print(f"Topic {topic_name} đã tồn tại.")
    except Exception as e:
        print(f"Lỗi khi tạo topic: {e}")

# Khởi tạo Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # Chờ tất cả broker xác nhận khi gửi
    batch_size=16384,
    linger_ms=10
)

# Comment phần Kafka Consumer dưới đây
# Khởi tạo Kafka Consumer
consumer = KafkaConsumer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id='books_consumer_group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    session_timeout_ms=90000,
    heartbeat_interval_ms=10000,
    max_poll_interval_ms=60000
)

# Đăng ký vào topic Kafka
consumer.subscribe([KAFKA_TOPIC])

# Đọc dữ liệu từ MongoDB và gửi đến Kafka
def stream_from_mongo_to_kafka(max_iterations=5, max_records_per_iteration=50):
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    collection = client[MONGO_DB][MONGO_COLLECTION]

    for iteration in range(max_iterations):
        print(f"Iteration {iteration + 1} bắt đầu.")
        records = []
        ids = []

        # Giới hạn số lượng bản ghi lấy mỗi lần
        for document in collection.find({"sent_to_kafka": {"$ne": True}}).limit(max_records_per_iteration):
            ids.append(document["_id"])
            document.pop("_id", None)  # Loại bỏ _id trước khi gửi
            records.append(document)

        if records:
            try:
                # Gửi dữ liệu đến Kafka
                print(f"Gửi {len(records)} bản ghi đến Kafka...")
                for record in records:  # Gửi từng bản ghi riêng biệt
                    producer.send(KAFKA_TOPIC, value=record)
                    producer.flush()  # Đảm bảo gửi thành công
                print(f"Đã gửi {len(records)} bản ghi đến Kafka.")
                
                # Đánh dấu các bản ghi đã gửi
                collection.update_many(
                    {"_id": {"$in": ids}},
                    {"$set": {"sent_to_kafka": True}}
                )
            except Exception as e:
                print(f"Lỗi khi gửi dữ liệu đến Kafka: {e}")
        
        if not records:
            print("Không còn bản ghi mới để gửi. Hoàn thành.")
            break

        sleep(1)

# Comment phần xử lý dữ liệu từ Kafka
# Hàm xử lý dữ liệu từ Kafka
def consume_from_kafka(max_messages=100, timeout=60):
    print(f"Consumer đã bắt đầu lắng nghe topic {KAFKA_TOPIC}...")

    # Đếm số lượng message đã nhận
    message_count = 0
    start_time = time.time()

    # Polling loop
    while message_count < max_messages and time.time() - start_time < timeout:
        # Poll from Kafka
        messages = consumer.poll(timeout_ms=1000, max_records=max_messages - message_count)

        if not messages:
            print("Không có tin nhắn mới trong khoảng thời gian chờ.")
            break
        
        for tp, messages in messages.items():
            for message in messages:
                print(f"Đã nhận dữ liệu từ Kafka: {message.value}")
                message_count += 1

                # Logic xử lý dữ liệu ở đây.
                consumer.commit()

                if message_count >= max_messages:
                    print(f"Đã đạt giới hạn {max_messages} tin nhắn. Dừng consumer.")
                    break

    print("Consumer đã dừng.")

# Chạy hàm tạo topic nếu chưa tồn tại
if __name__ == "__main__":
    create_topic_if_not_exists(KAFKA_TOPIC)  # Kiểm tra và tạo topic nếu cần
    
    # Chạy hàm stream dữ liệu từ MongoDB đến Kafka
    stream_from_mongo_to_kafka(max_iterations=5, max_records_per_iteration=50)
    
    # Comment phần chạy consumer
    # Chạy consumer để lắng nghe và xử lý dữ liệu từ Kafka
    consume_from_kafka(max_messages=100, timeout=60)  # Giới hạn 100 tin nhắn hoặc 60 giây






#note: bản này quan trọng - chạy oke 
# import os
# import json
# from kafka.admin import KafkaAdminClient, NewTopic
# from kafka import KafkaProducer, KafkaConsumer
# from pymongo import MongoClient
# from time import sleep
# import time

# # Cấu hình MongoDB
# MONGO_HOST = os.getenv('MONGO_HOST', 'mymongodb_container')
# MONGO_PORT = 27017
# MONGO_DB = 'books_data_KimDong_12'
# MONGO_COLLECTION = 'books_KimDong'

# # Cấu hình Kafka
# KAFKA_TOPIC = 'books_topic'
# KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka_container:29092')

# # Khởi tạo Kafka Admin Client để kiểm tra và tạo topic nếu cần
# admin_client = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

# # Hàm để tạo topic nếu chưa tồn tại
# def create_topic_if_not_exists(topic_name):
#     try:
#         # Kiểm tra nếu topic đã tồn tại
#         topics = admin_client.list_topics()
#         if topic_name not in topics:
#             print(f"Topic {topic_name} chưa tồn tại, đang tạo mới...")
#             new_topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
#             admin_client.create_topics(new_topics=[new_topic], validate_only=False)
#             print(f"Topic {topic_name} đã được tạo.")
#         else:
#             print(f"Topic {topic_name} đã tồn tại.")
#     except Exception as e:
#         print(f"Lỗi khi tạo topic: {e}")

# # Khởi tạo Kafka Producer
# producer = KafkaProducer(
#     bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
#     value_serializer=lambda v: json.dumps(v).encode('utf-8'),
#     acks='all',  # Chờ tất cả broker xác nhận khi gửi
#     batch_size=16384,
#     linger_ms=10
# )

# #Comment phần Kafka Consumer dưới đây
# #Khởi tạo Kafka Consumer
# consumer = KafkaConsumer(
#     bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
#     group_id='books_consumer_group',  # Đặt tên cho consumer group
#     value_deserializer=lambda m: json.loads(m.decode('utf-8')),  # Chuyển đổi dữ liệu từ Kafka
#     auto_offset_reset='earliest',  # Đọc từ vị trí đầu tiên nếu là consumer mới earliest
#     enable_auto_commit=False,  # Tự động commit offset khi xử lý xong tin nhắn
#     session_timeout_ms=90000,  # Tăng thời gian session timeout
#     heartbeat_interval_ms=10000,  # Giảm thời gian heartbeat để nhận phản hồi nhanh hơn
#     max_poll_interval_ms=60000
# )

# #Đăng ký vào topic Kafka
# consumer.subscribe([KAFKA_TOPIC])  # Đăng ký vào topic cụ thể

# # Đọc dữ liệu từ MongoDB và gửi đến Kafka
# def stream_from_mongo_to_kafka(max_iterations=5, max_records_per_iteration=50):
#     client = MongoClient(MONGO_HOST, MONGO_PORT)
#     collection = client[MONGO_DB][MONGO_COLLECTION]

#     for iteration in range(max_iterations):
#         print(f"Iteration {iteration + 1} bắt đầu.")
#         records = []
#         ids = []
        
#         # Giới hạn số lượng bản ghi lấy mỗi lần
#         for document in collection.find({"sent_to_kafka": {"$ne": True}}).limit(max_records_per_iteration):
#             ids.append(document["_id"])
#             document.pop("_id", None)  # Loại bỏ _id trước khi gửi
#             records.append(document)

#         if records:
#             try:
#                 # Gửi dữ liệu đến Kafka
#                 print(f"Gửi {len(records)} bản ghi đến Kafka...")
#                 producer.send(KAFKA_TOPIC, value=records)
#                 #producer.send(KAFKA_TOPIC, value=json.dumps(records))
#                 producer.flush()  # Đảm bảo gửi thành công
#                 print(f"Đã gửi {len(records)} bản ghi đến Kafka.")
                
#                 # Đánh dấu các bản ghi đã gửi
#                 collection.update_many(
#                     {"_id": {"$in": ids}},
#                     {"$set": {"sent_to_kafka": True}}
#                 )
#             except Exception as e:
#                 print(f"Lỗi khi gửi dữ liệu đến Kafka: {e}")
        
#         if not records:
#             print("Không còn bản ghi mới để gửi. Hoàn thành.")
#             break

#         sleep(1)

# # Comment phần xử lý dữ liệu từ Kafka
# # Hàm xử lý dữ liệu từ Kafka
# def consume_from_kafka(max_messages=100, timeout=60):
#     print(f"Consumer đã bắt đầu lắng nghe topic {KAFKA_TOPIC}...")

#     # Đếm số lượng message đã nhận
#     message_count = 0
#     start_time = time.time()

#     # Polling loop
#     while message_count < max_messages and time.time() - start_time < timeout:
#         # Poll from Kafka
#         messages = consumer.poll(timeout_ms=1000, max_records=max_messages - message_count)

#         if not messages:
#             print("Không có tin nhắn mới trong khoảng thời gian chờ.")
#             break
        
#         for tp, messages in messages.items():
#             for message in messages:
#                 print(f"Đã nhận dữ liệu từ Kafka: {message.value}")
#                 message_count += 1

#                 # Nếu bạn muốn xử lý dữ liệu ở đây, ví dụ lưu vào MongoDB hoặc in ra
#                 # Logic xử lý dữ liệu ở đây.
#                 consumer.commit()

#                 if message_count >= max_messages:
#                     print(f"Đã đạt giới hạn {max_messages} tin nhắn. Dừng consumer.")
#                     break

#     print("Consumer đã dừng.")

# # Chạy hàm tạo topic nếu chưa tồn tại
# if __name__ == "__main__":
#     create_topic_if_not_exists(KAFKA_TOPIC)  # Kiểm tra và tạo topic nếu cần
    
#     # Chạy hàm stream dữ liệu từ MongoDB đến Kafka
#     stream_from_mongo_to_kafka(max_iterations=5, max_records_per_iteration=50)
    
#     # Comment phần chạy consumer
#     # Chạy consumer để lắng nghe và xử lý dữ liệu từ Kafka
#     consume_from_kafka(max_messages=100, timeout=60)  # Giới hạn 100 tin nhắn hoặc 60 giây


























