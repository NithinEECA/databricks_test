# Databricks notebook source
import dlt
from pyspark.sql import functions as F
# Define the source catalog and schema
source_catalog = "hub_dev_bronze"
source_schema = "salesforce"
table_names = ["account", "contact"]
# Create a view to stage the contacts data
@dlt.view
def stage_account():
    return (
        spark.readStream
        .format("delta")
        .table(f"{source_catalog}.{source_schema}.{table_names[0]}")
        .select("Id", "Name", "ETL_LoadDate")  # Select only the necessary columns
    )

# Create the target table
dlt.create_target_table(
    name=table_names[0],
    comment="This is the target table for accounts.",
    table_properties={
        "delta.columnMapping.mode": "name",
        'delta.minReaderVersion' : '2',
        'delta.minWriterVersion' : '5'
    }
)

# Apply the changes from the staged view to the target table
dlt.apply_changes(
    target=f"{table_names[0]}",
    source=f"stage_{table_names[0]}",
    keys=["Id"],
    sequence_by=F.col("ETL_LoadDate"),
    stored_as_scd_type=1
)
# Create a view to stage the contacts data
@dlt.view
def stage_contact():
    return (
        spark.readStream
        .format("delta")
        .table(f"{source_catalog}.{source_schema}.{table_names[1]}")
        .select("Id", "Email", "ETL_LoadDate")
    )

# Create the target table
dlt.create_target_table(
    name=table_names[1],
    comment="This is the target table for contacts.",
    table_properties={
        "delta.columnMapping.mode" : "name",
        'delta.minReaderVersion' : '2',
        'delta.minWriterVersion' : '5'
    }
)

# Apply the changes from the staged view to the target table
dlt.apply_changes(
    target=f"{table_names[1]}",
    source=f"stage_{table_names[1]}",
    keys=["Id"],
    sequence_by=F.col("ETL_LoadDate"),
    stored_as_scd_type=1
)