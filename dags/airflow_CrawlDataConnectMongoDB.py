from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.docker.operators.docker import DockerOperator
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

# Tạo DAG
with DAG(
    'run_app_crawler_compose',
    default_args=default_args,
    description='Run Docker container for app_crawlData_KimDong using BashOperator',
    schedule_interval=None,  # Thực thi thủ công
    start_date=datetime(2023, 1, 1),
    catchup=False,
) as dag:

    #demo 1 - Task: khởi chạy container crawl dữ liệu 
    # run_app_crawler_compose = BashOperator(
    #     task_id="run_app_crawler_compose",
    #     bash_command="docker start -ai app_crawldata_kimdong",
    # )

    #demo 2 - Task: bản hoàn thành 
    task_run_entrypoint = DockerOperator(
    task_id='run_entrypoint_sh',
    image='detai_phantichdinhluong_webkimdong-main_version2_pyspark_windows_airflow-app_crawldata_kimdong',
    command='bash -c "/usr/src/app/entrypoint.sh"',  # Chạy entrypoint.sh thông qua bash
    dag=dag,
    auto_remove=True,
    network_mode='detai_phantichdinhluong_webkimdong-main_version2_pyspark_windows_airflow_my_network',  # Kết nối container này vào mạng 'my_network' giống như trong Docker Compose
    )


    


    








