# Databricks notebook source
import requests
import json
from pyspark.sql import SparkSession
import datetime
import concurrent.futures
from pyspark.sql.types import StructType, StructField, StringType
import pyspark.sql.functions as F

object_file_path = f"/Volumes/hub_dev_bronze/salesforce/raw_files_sf/sf_objects.txt"

# Function to read Salesforce object names from the file
def read_object_names(file_path):
    with open(file_path, 'r') as file:
        object_names = [line.strip() for line in file.readlines()]
    return object_names

sl_object_names = read_object_names(object_file_path)

def fetch_and_save_data(sl_object_name):
    current_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # Define the output path with the timestamp
    output_path = f"/Volumes/hub_dev_bronze/salesforce/raw_files_sf/{sl_object_name}/{sl_object_name}_{current_timestamp}/" 
    
    try:
        # Salesforce credentials
        client_id = dbutils.secrets.get(scope="dev_kv_salesforce_password_preprod", key="salesforce-readonly-key-preprod")
        client_secret = dbutils.secrets.get(scope="dev_kv_salesforce_password_preprod", key="Salesforce-readonly-secret-preprod")
        username = dbutils.secrets.get(scope="dev_kv_salesforce_password_preprod", key="salesforce-readonly-username-preprod")
        password = dbutils.secrets.get(scope="dev_kv_salesforce_password_preprod", key="salesforce-readonly-password-preprod")
        token = dbutils.secrets.get(scope="dev_kv_salesforce_password_preprod", key="salesforce-readonly-token-preprod")
        login_url = 'https://eeca--preprod.sandbox.my.salesforce.com/services/oauth2/token'

        # Step 1: Authenticate and get access token
        auth_data = {
            'grant_type': 'password',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username,
            'password': password
        }

        response = requests.post(login_url, data=auth_data)
        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            access_token = response_data['access_token']
            instance_url = response_data['instance_url']
            print("Access token obtained successfully")
        else:
            print("Failed to obtain login access token")
            print(f"Status Code for {sl_object_name}: {response.status_code}")
            print(response.json())
            exit()

        # Step 2: Get the list of all fields for the object_name using describe
        describe_url = f'{instance_url}/services/data/v52.0/sobjects/{sl_object_name}/describe'
        headers = {
                 'Authorization': f'Bearer {access_token}',
                 'Content-Type': 'application/json'
        }
        response = requests.get(describe_url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            fields = [field['name'] for field in data['fields']]

            # Step 3: Construct the SOQL query dynamically using all fields
            field_string = ', '.join(fields)
            query = f"SELECT {field_string} FROM {sl_object_name}"
            query_url = f'{instance_url}/services/data/v52.0/query/?q={query}'

            # Step 4: Query Salesforce Account object with all fields
            response = requests.get(query_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                records = data['records']

                # Step 5: Convert records into list of dictionaries and cast values to strings
                record_list = [{k: str(v) for k, v in record.items()} for record in records]

                # Step 6: Define schema where all fields are StringType
                schema = StructType([StructField(field, StringType(), True) for field in fields])

                spark = SparkSession.builder.appName(f'SalesforceData_{sl_object_name}').getOrCreate()
                df = spark.createDataFrame(record_list, schema=schema)

                # Write to the existing Unity Catalog Volume (Delta format recommended)
                df.write.format("parquet").mode("overwrite").save(output_path)
                print(f"Data successfully saved")
            else:
                print("Failed to retrieve data")
                print(f"Status Code for {sl_object_name}: {response.status_code}")
                print(response.json())
        else:
            print("Failed to obtain access token")
            print(f"Status Code for {sl_object_name}: {response.status_code}")

    except Exception as e:
        print(f"Error processing {sl_object_name}: {str(e)}")

# Using ThreadPoolExecutor to run in parallel
with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(fetch_and_save_data, sl_object_names)