from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from pymongo import MongoClient
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import Producer, Consumer
import json
import os
from time import sleep, time
from datetime import datetime, timedelta

# Định nghĩa thông số cơ bản của DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Cấu hình MongoDB và Kafka
MONGO_HOST = os.getenv('MONGO_HOST', 'mymongodb_container')
MONGO_PORT = 27017
MONGO_DB = 'books_data_KimDong_12'
MONGO_COLLECTION = 'books_KimDong'
KAFKA_TOPIC = 'books_topic'
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka_container:29092')

# Hàm để tạo topic nếu chưa tồn tại
def create_topic_if_not_exists():
    try:
        admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
        topics = admin_client.list_topics(timeout=10).topics

        if KAFKA_TOPIC not in topics:
            print(f"Topic {KAFKA_TOPIC} chưa tồn tại, đang tạo mới...")
            new_topic = NewTopic(KAFKA_TOPIC, num_partitions=1, replication_factor=1)
            admin_client.create_topics([new_topic])
            print(f"Topic {KAFKA_TOPIC} đã được tạo.")
        else:
            print(f"Topic {KAFKA_TOPIC} đã tồn tại.")
    except Exception as e:
        print(f"Lỗi khi tạo topic: {e}")

# Hàm để stream dữ liệu từ MongoDB tới Kafka
def stream_from_mongo_to_kafka():
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    collection = client[MONGO_DB][MONGO_COLLECTION]
    ids = []

    # Lấy tất cả các bản ghi chưa gửi tới Kafka
    records = []
    cursor = collection.find({"sent_to_kafka": {"$ne": True}})

    # Giới hạn số lượng bản ghi gửi mỗi lần
    for document in cursor:
        ids.append(document["_id"])
        document.pop("_id", None)  # Loại bỏ _id trước khi gửi
        records.append(document)

    if records:
        try:
            producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
            for record in records:  # Gửi từng bản ghi riêng biệt
                producer.produce(KAFKA_TOPIC, value=json.dumps(record))
            producer.flush()  # Đảm bảo tất cả dữ liệu được gửi
            print(f"Đã gửi {len(records)} bản ghi đến Kafka.")

            # Đánh dấu các bản ghi đã gửi
            collection.update_many(
                {"_id": {"$in": ids}},
                {"$set": {"sent_to_kafka": True}}
            )
        except Exception as e:
            print(f"Lỗi khi gửi dữ liệu đến Kafka: {e}")
    else:
        print("Không còn bản ghi mới để gửi.")

# Hàm để tiêu thụ dữ liệu từ Kafka
def consume_from_kafka():
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'books_consumer_group',
        'auto.offset.reset': 'earliest'
    })
    consumer.subscribe([KAFKA_TOPIC])

    print(f"Consumer đã bắt đầu lắng nghe topic {KAFKA_TOPIC}...")
    message_count = 0
    max_messages = 100
    timeout = 60  # Giới hạn thời gian chờ là 60 giây
    start_time = time()

    while message_count < max_messages and time() - start_time < timeout:
        messages = consumer.consume(timeout=1.0, num_messages=max_messages - message_count)
        if not messages:
            print("Không có tin nhắn mới trong khoảng thời gian chờ.")
            break

        for message in messages:
            if message.error():
                print(f"Lỗi khi nhận tin nhắn: {message.error()}")
                continue

            print(f"Đã nhận dữ liệu từ Kafka: {message.value().decode('utf-8')}")
            message_count += 1

            if message_count >= max_messages:
                print(f"Đã đạt giới hạn {max_messages} tin nhắn. Dừng consumer.")
                break

    consumer.close()
    print("Consumer đã dừng.")

# Tạo DAG
with DAG(
    'complete_dag_for_crawling_mongo_kafka_spark_Postgres',
    default_args=default_args,
    description='Complete workflow for app_crawldata_kimdong, MongoDB to Kafka streaming, and Spark container to Postgres',
    schedule_interval=None,  # Thực thi thủ công
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:

    # Task 1: Chạy container app_crawldata_kimdong
    task_run_entrypoint = DockerOperator(
        task_id='run_app_crawler_compose',
        image='detai_phantichdinhluong_webkimdong-main_version2_pyspark_windows_airflow-app_crawldata_kimdong',
        command='bash -c "/usr/src/app/entrypoint.sh"',  # Chạy entrypoint.sh thông qua bash
        dag=dag,
        auto_remove=True,
        network_mode='detai_phantichdinhluong_webkimdong-main_version2_pyspark_windows_airflow_my_network',  # Kết nối container này vào mạng 'my_network' giống như trong Docker Compose
    )

    # Task 2: Tạo topic Kafka nếu chưa tồn tại
    create_topic_task = PythonOperator(
        task_id='create_kafka_topic',
        python_callable=create_topic_if_not_exists
    )

    # Task 3: Stream dữ liệu từ MongoDB đến Kafka
    stream_to_kafka_task = PythonOperator(
        task_id='stream_to_kafka',
        python_callable=stream_from_mongo_to_kafka
    )

    # Task 4: Tiêu thụ dữ liệu từ Kafka
    consume_from_kafka_task = PythonOperator(
        task_id='consume_from_kafka',
        python_callable=consume_from_kafka
    )

    # Task 5: Chạy container Spark - Spark đọc dữ liệu từ kafka_container xử lý dữ liệu sau đó đẩy vào postgreSQL
    run_spark_container_compose = BashOperator(
        task_id="run_spark_container_compose",
        bash_command="""docker start -ai spark_container || exit 1
        echo "Container finished running."
        """,
    )

    # Xác định thứ tự chạy các task
    task_run_entrypoint >> create_topic_task >> stream_to_kafka_task >> consume_from_kafka_task >> run_spark_container_compose
