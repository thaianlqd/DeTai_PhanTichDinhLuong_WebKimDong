from airflow import DAG
from airflow.operators.bash import BashOperator
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
    'run_spark_container_compose',
    default_args=default_args,
    description='Run Docker container for Spark using BashOperator',
    schedule_interval=None,  # Thực thi thủ công
    start_date=datetime(2023, 1, 1),
    catchup=False,
) as dag:

    # Task: Chạy container Spark
    # run_spark_container_compose = BashOperator(
    #     task_id="run_spark_container_compose",
    #     bash_command="docker start -ai spark_container",
    # )

    run_spark_container_compose = BashOperator(
    task_id="run_spark_container_compose",
    bash_command="""
    docker start -ai spark_container || exit 1
    echo "Container finished running."
    """,
    )
