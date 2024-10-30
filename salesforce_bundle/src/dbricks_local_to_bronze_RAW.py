# Databricks notebook source
import dlt
import pyspark.sql.functions as F
import datetime

# Set up Spark configuration
spark.conf.set("spark.sql.files.ignoreMissingFiles", "true")

# Path to the file containing Salesforce object names
object_file_path = f"/Volumes/hub_dev_bronze/salesforce/raw_files_sf/sf_objects.txt"

# Function to read Salesforce object names from a file
def read_object_names(file_path):
    with open(file_path, 'r') as file:
        object_names = [line.strip() for line in file.readlines()]
    return object_names

# COMMAND Auto Loader----------
def readstream_files(name):
    raw_path = f"/Volumes/hub_dev_bronze/salesforce/raw_files_sf/{name}"
    df = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option("mergeSchema", "true")
        .option("recursiveFileLookup", "true")     
        #.option("cloudFiles.inferColumnTypes", "true")
        #.option("cloudFiles.schemaHints", "IsDeleted BOOLEAN")        
    ).load(raw_path)
    return  df

# Get the list of Salesforce objects from the file
salesforce_objects = read_object_names(object_file_path)

# Create DLT tables dynamically for each Salesforce object
for obj in salesforce_objects:
    @dlt.table(name=obj.lower(), comment=f"{obj} table")
    def create_table(obj=obj):
        return readstream_files(obj).withColumn("ETL_InputFile", F.col("_metadata.file_path")).withColumn("ETL_LoadDate", F.lit(datetime.datetime.now()))   

#@dlt.table(name="account", comment="Account table")
#def account_table():
#    return readstream_files("Account").withColumn("ETL_InputFile", F.col("_metadata.file_path")
#    ).withColumn("ETL_LoadDate", F.lit(datetime.datetime.now()))
#
#@dlt.table(name="Contact", comment="Contact table")
#def contact_table():
#    return readstream_files("Contact").withColumn("ETL_InputFile", F.col("_metadata.file_path")
#    ).withColumn("ETL_LoadDate", F.lit(datetime.datetime.now()))
#
#@dlt.table(name="PricebookEntry", comment="PricebookEntry table")
#def pricebookentry_table():
#    return readstream_files("PricebookEntry").withColumn("ETL_InputFile", F.col("_metadata.file_path")
#    ).withColumn("ETL_LoadDate", F.lit(datetime.datetime.now()))