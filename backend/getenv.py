# this is a constant file that get all the environment variables
# import libraries
import os

from dotenv import load_dotenv
load_dotenv()

# getting mongodb connection credentials
mongodb_username = os.getenv('MONGO_DB_USERNAME')
mongodb_password = os.getenv('MONGO_DB_PASSWORD')

# getting mysql connection credentials
psql_username = os.getenv('DB_USERN')
psql_password = os.getenv('DB_PASS')
psql_host = os.getenv('DB_HOST')
psql_port = os.getenv('DB_PORT')
psql_db_name = os.getenv('DB_NAME')
