import os
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, FloatType
from pyspark.sql.functions import from_json, col

# Konfiguracja polaczenia z baza danych
db_host = os.environ.get("MYSQL_HOST", "mysql-service")
db_port = os.environ.get("MYSQL_DB_PORT", "3306")
db_url = f"jdbc:mysql://{db_host}:{db_port}/behavior_db"

# Inicjalizacja sesji Sparka (z dociagnieciem sterownikow Kafki i MySQL w locie)
spark = SparkSession.builder \
    .appName("VideoAnalyticsStreaming") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,mysql:mysql-connector-java:8.0.33") \
    .getOrCreate()

# Wyciszamy zbedne logi Sparka, zeby widziec tylko to co wazne
spark.sparkContext.setLogLevel("WARN")

# Definiujemy twardy schemat, jakiego oczekujemy od Kafki
schema = StructType([
    StructField("camera_id", StringType(), True),
    StructField("video_name", StringType(), True),
    StructField("person_id", StringType(), True),
    StructField("behavior", StringType(), True),
    StructField("speed", FloatType(), True),
    StructField("confidence", FloatType(), True)
])

# Czytamy surowy strumien bajtów z Kafki na biezaco (latest)
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka-service:9092") \
    .option("subscribe", "detections") \
    .option("startingOffsets", "latest") \
    .load()

# Transformacja: Zamieniamy bajty na tekst, a tekst parsujemy wedlug naszego schematu
parsed_df = kafka_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

# Funkcja ladujaca pojedyncza "wywrotke" (batch) do bazy MySQL
def write_to_mysql(df, epoch_id):
    df.write.jdbc(
        url=db_url,
        table="detections",
        mode="append",
        properties={"user": "root", "password": "infostrateg_root", "driver": "com.mysql.cj.jdbc.Driver"}
    )

# Zapisujemy strumien "w locie" zrzucajac pakiety co 5 sekund
query = parsed_df.writeStream \
    .foreachBatch(write_to_mysql) \
    .trigger(processingTime="5 seconds") \
    .start()

query.awaitTermination()