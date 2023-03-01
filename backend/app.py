from flask import Flask, jsonify, render_template, redirect, url_for, request, send_from_directory, session
from sqlalchemy import create_engine, MetaData, inspect
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource
from sqlalchemy.orm import scoped_session, sessionmaker
from pyignite import Client
from database_model.models import db, Station, Users
import os
import sys
import asyncio
import websockets
from flask_socketio import SocketIO, emit
import pdb
# import the modules
# main_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# sys.path.append(main_directory)
# import main

# connect flask to the database
app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///martinrea.db'
app.config['SERVER_NAME'] = '127.0.0.1:5000'
app.config['APPLICATION_ROOT'] = '/'
app.config['PREFERRED_URL_SCHEME'] = 'http'

# Create SQLALCHEMY database object
db.init_app(app)
# create all the tables based on the models if they didn't exist yet
with app.app_context():
  inspector = inspect(db.engine)
  if not inspector.has_table('station') and not inspector.has_table('users'):
    
    db.create_all()

# app.config['SECRET_KEY'] = 'secret!'
# socketio = SocketIO(app)
# db.init_app(app)

# @socketio.on('connect', namespace='/bt1xx/station/<int:station_number>/settings')
# def test_connect():
#   emit('my response', {'data': 'Connected'})

# # connect the python server to the web socket
# async def handle_key_events(websocket, path):
#   async for message in websocket:
#     # Process the key code received from the client
#     if message == ",": # Key code for ","
#       print(",")
#     elif message == ".": # Key code for "."
#       print(".")
#     elif message == "k": # Key code for "k"
#       print("k")
#     elif message == "l": # Key code for "l"
#       print("l")

# # Start the WebSocket server 
# async def start_server():
#   # Set the WebSocket server URL
#   server_url = "http://127.0.0.1:5000/bt1xx/station/<int:station_number>/settings"

#   # Start the WebSocket Server
#   async with websockets.serve(handle_key_events, server_url):
#     await asyncio.Future() # Run the server indefinitely

# asyncio.run(start_server())

# client = Client()
# client.connect('10.10.10.33', 8088)

# app.config['SQL_ALCHEMY_URI'] = 'ignite://10.10.10.33:8088/Hydroform'
# db = SQLAlchemy(app)

# # create the Ignite engine and connect to the server
# engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], module='sqlalchemy_ignite.pyignite')
# engine.connect()

# include the path to javascript files
@app.route('/static-js/<path:filename>')
# add the static files path towards the javascript files
def serve_static_js(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/static-js'), filename)

# include the path to css static files
@app.route('/static-css/<path:filename>')
# add the static files path towards the css files
def serve_static_css(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/static-css'), filename)

# include the path to the photos files
@app.route('/Photos/<path:filename>')
# add the photos files path towards the html
def serve_static_photos(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/Photos'), filename)

####################### HOMEPAGE ##########################
# render the homepage
@app.route('/bt1xx/home/')
def homepage():
 return render_template("home.html")

####################### STATION DETAILS #####################
# render the station details depends on the click event 
@app.route('/bt1xx/station/<int:station_number>/')
def station_detail(station_number):
  return render_template("station_details.html", station_number=station_number)

###################### STATION SETTINGS ######################
# render the station settings:
@app.route('/bt1xx/station/<int:station_number>/settings')
def station_settings(station_number):
  # # import capture function from imageCaptureClasses
  # captureObject = main.captureObject

  # # import paramSetup function to set the focal length and the brightness of the camera (camera settings)
  # result = main.paramsSetup(station_selected, captureObject, recalibrate=True)

  return render_template("station_settings.html", station_number=station_number)

###################### STATION CHANGE SETTINGS #################
# retrieve the data from the form
@app.route('/bt1xx/station/<int:station_number>/changeSettings', methods=['POST'])
def change_settings(station_number):
  if request.method == 'POST':
    try:
      pdb.set_trace()
      # insert into the station detail table
      station_selected = station_number
      focal_length_settings = request.form['focal_length_setting_input']
      brightness_setting = request.form['brightness_setting_input']
      white_balance_lock_data = bool(request.form['white_balance_lock_input'])
      auto_exposure_lock_data = bool(request.form['auto_exposure_lock'])

      # create a list of new setting instance
      new_settings = [
        Station(station_number=station_selected, station_focalLength=focal_length_settings,station_brightness=brightness_setting,white_balance_lock=white_balance_lock_data, auto_exposure_lock = auto_exposure_lock_data)
      ]

      # add new setting into the station model
      for setting in new_settings:
        try:
          db.session.add(setting)
          # commit the change to the database
          db.session.commit()
          print(f"Setings for station {setting.station_number} added successfully!")
        except:
          db.session.rollback()
          print(f"Settings for station {setting.station_number} already existed!")

      result = Station.query.filter_by(station_number=station_selected).first()

      if result:
        print(f"Data has been inserted successfully!")
        return redirect(url_for('station_detail', station_number = station_number))
      else:
        print(f"Error inserting data into the database")
        pass

    # catch the error if the requirements are not met by the database
    except:
      db.session.rollback()
      print(f"There is an error while inserting the data into the database!")
      return redirect(url_for('station_settings', station_number=station_selected))
  
  # return render_template("successful.html", station_number=station_number)

################################# LOG IN PAGE #############################
# render the login page
@app.route('/bt1xx/login/')
def login():
  return render_template('login.html')

# authenticate the users login
@app.route('/bt1xx/authentication/', methods=['POST', 'GET'])
def authentication():
  username = request.form['username']
  password = request.form['password']
  
  return redirect(url_for('homepage'))

if __name__ == '__main__':
 app.run(debug=True)








