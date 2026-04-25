FROM apache/airflow:2.7.1

USER root

# Install OpenJDK-11
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         openjdk-11-jre-headless \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

# Install PySpark and Providers
RUN pip install --no-cache-dir \
    "apache-airflow==2.7.1" \
    pyspark==3.5.0 \
    apache-airflow-providers-apache-spark \
    apache-airflow-providers-amazon \
    numpy==1.24.4
