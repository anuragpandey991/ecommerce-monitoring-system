import psycopg2
from psycopg2.extras import Json
import os

def get_connection():
    
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="ecommerce",
        user="postgres",
        password="postgres"
    )
