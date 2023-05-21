# import required libraries
from flask import Flask, jsonify, render_template, redirect, url_for, request, send_from_directory, make_response, jsonify, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine.reflection import Inspector
from flask_restful import Api
from sqlalchemy import create_engine, MetaData, inspect
from http import HTTPStatus
from bson import json_util
import bcrypt
import jwt
import os
from flask_migrate import Migrate
import secrets
import depthai as dai
import json
from datetime import datetime, timedelta
import pytz
import pdb
import requests
import uuid

# import files
from database_model.models import db, Station, Users, Permission, TimingStation100, TimingStation120
from helper_functions.validate_users import validate_username, validate_password, give_permission
from helper_functions.middleware_function import validate_token
from helper_functions.run_all_cameras import run_all_cameras
from helper_functions.insert_users import mongo_db, users_collection # mongodb connection
from imageCalibrationClass import Recalibration, createPipeline
from getenv import psql_db_name, psql_host, psql_password, psql_username, psql_port

# read in the params.json file
with open(r'params.json') as f:
  partList = json.load(f)

# connect flask to the sqlite database
app = Flask(__name__)
api = Api(app)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instances/martinrea.db'
# database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgres://{psql_username}:{psql_password}@{psql_host}:{psql_port}/{psql_db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# engine = create_engine('sqlite:///instances/martinrea.db')
engine = create_engine(f'postgres://{psql_username}:{psql_password}@{psql_host}:{psql_port}/{psql_db_name}')
app.config['APPLICATION_ROOT'] = '/'
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.config['CORS_HEADERS'] = 'Content-Type'

# secret key
app.config['SECRET_KEY'] = secrets.token_hex(16)

db.init_app(app)
 
CORS(app)

inspector = Inspector.from_engine(engine)

# generate a 32-character hexadecimal secret key for users to login their session
app.secret_key = secrets.token_hex(16)
migrate = Migrate(app, db)

all_tables_name = ['stations_settings', 'admin_users', 'admin_permissions', 'Station100_Timing', 'Station120_Timing']
# Create SQLALCHEMY database object
def create_tables():
  with app.app_context():
    try:
      db.metadata.bind = engine
      tables_names = inspector.get_table_names()
      for i in all_tables_name:
        if i in tables_names:
          return
        
      db.create_all()
      return
    except Exception as error:
      print(f"There was an error while creating tables in the database: {error}")
      return

create_tables()

# insert into users table
@app.route('/bt1xx/insert-admin-users/', methods=['GET'])
def insert_admin_users():
  with app.app_context():
    # create a list of non-encoded username and passwords
    # read in the users.json file
    with open('users.json', 'r') as f:
      user = json.load(f)
    
    names = []
    usernames = []
    passwords = []
    is_admin = []

    try:
      # get the list of usernames and passwords
      for i in range(5):
        names.append(user[f'user{i}']['name'])
        usernames.append(user[f'user{i}']['username'])
        passwords.append(user[f'user{i}']['password'])
        is_admin.append(user[f'user{i}']['is_admin'])

      # validate the username and password constraints before hashing it and put it into the database
      for i in range(len(usernames)):
        if validate_username(usernames[i]):
          decoded_salt, hashed_password = validate_password(usernames[i], passwords[i], Users)

          # create an instance to insert rows into user table
          new_users = [
            Users(id=i+1, name=names[i], username=usernames[i], password=hashed_password, password_salt=decoded_salt, is_admin=is_admin[i])
          ]

          for user in new_users:
            # insert the new user into the session
            try:
              db.session.add(user)
              print(f"User {user.username} added successfully!")
            except:
              db.session.rollback()
              print(f"User {user.username} already exists in the database!")
              return jsonify({
                'message' : f'Sorry user {user.username} already existed in the database!'
              }), 409
          
          # read in permissions.json
          with open('permissions.json', 'r') as f:
            permissions = json.load(f)

          users_permissions_list = []
          admin_permissions_list = []
          # get the 2 lists of permissions
          for i in range(2):
            users_permissions_list.append(permissions['all_users_permissions'][f'permission{i}']['permission_name'])
          
          for i in range(19):
            admin_permissions_list.append(permissions['admin_permissions'][f'permission{i}']['permission_name'])

          # put the permissions into the permission table
          give_permission(Permission, Users, users_permissions_list, admin_permissions_list, db)
          response_data = ({
            'message' : "Successfully insert admin users and permissions!"
          })

      # commit the changes to the database
      db.session.commit()
      # return a json response to a client
      response_json = json.dumps(response_data)
      response = Response(response_json, status=HTTPStatus.CREATED, mimetype='application/json')
      return response

    except Exception as error:
      response_data = ({
        'message' : f'There is an internal server error while inserting admin users into the database: {error}'
      })
      response_json = json.dumps(response_data)
      response = Response(response_json, status=HTTPStatus.CREATED, mimetype='application/json')
      return response

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

# include the path to the logo files
@app.route('/Logos/<path:filename>')
# add the logo files path towards the html
def serve_static_photos(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/Logos'), filename)

# include the path to the photo folder to get the files in the station 100 mask folder
@app.route('/Photos/Masks/station100/<path:filename>')
# add the photo files path towards the html
def serve_static_mask_100(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/Photos/Masks/station100'), filename)

# include the path to the photo folder to get the files in the station 120 mask folder
@app.route('/Photos/Masks/station120/<path:filename>')
# add the photo files path towards the html
def serve_static_mask_120(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/Photos/Masks/station120'), filename)

# include the path to the photo folder to get the files in the station 100 ref folder
@app.route('/Photos/Refs/station100/<path:filename>')
# add the photo files path towards the html
def serve_static_ref_100(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/Photos/Refs/station100'), filename)

# include the path to the photo folder to get the files in the station 120 ref folder
@app.route('/Photots/Refs/station120/<path:filename>')
# add the photo files path towards the html
def serve_static_ref_120(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/Photos/Refs/station120'), filename)

# include the path to all the json files
@app.route('/<path:filename>')
# add the json file path towards the templates
def serve_static_json(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/'), filename)

# include the path to database
@app.route('/instances/<path:filename>')
# add the database path 
def serve_static_db(filename):
  root_dir = os.path.dirname(os.getcwd())
  return send_from_directory(os.path.join(root_dir, 'backend/instances/'), filename)

####################### HOMEPAGE ##########################
# define the list of permissions to visit this homepage
# render the homepage
@app.route('/bt1xx/home/')
@validate_token('homepage_access')
def homepage():
  # decode the token and get the name of the user
  token = request.cookies.get('token')
  name = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['name']
  return render_template('home.html', user_name=name)

 
####################### STATION DETAILS #####################
# render the station details depends on the click event 
@app.route('/bt1xx/station/<int:station_number>/')
@validate_token('station_detail')
def station_detail(station_number):
  # get the token from cookies
  token = request.cookies.get('token')
  name = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['name']
  # query the database to get the latest focal length, brightness, white balanace lock and auto exposure lock
  find_latest_settings = Station.query.filter_by(station_number=station_number).order_by(Station.id.desc()).first()

  # get the passref from the json
  station_passref = partList[f"station{station_number}"]['passref']

  if find_latest_settings:
    latest_focal_length = find_latest_settings.station_focalLength
    latest_brightness = find_latest_settings.station_brightness
    latest_white_balance_lock = find_latest_settings.white_balance_lock
    latest_auto_exposure = find_latest_settings.auto_exposure_lock

    # if the station is station 100:
    if station_number == 100:
      return render_template("station_details.html", station_number=station_number, user_name=name, focal_length_100=latest_focal_length, brightness_100=latest_brightness, white_balance_100=latest_white_balance_lock, exposure_lock_100=latest_auto_exposure, station_passref=station_passref)
    else:
      return render_template("station_details.html", station_number=station_number, user_name=name, focal_length_120=latest_focal_length, brightness_120=latest_brightness, white_balance_120=latest_white_balance_lock, exposure_lock_120=latest_auto_exposure, station_passref=station_passref)
  else:
    print('No status found!')
    return render_template("station_details.html", station_number=station_number, user_name=name, station_passref=station_passref)

###################### STATION SETTINGS ######################
# render the station settings
@app.route('/bt1xx/station/<int:station_number>/settings/')
@validate_token('station_settings')
def station_settings(station_number):
  try:
    return render_template('station_settings.html', station_number=station_number)
  
  except Exception as e:
    print(f"Error:" + str(e))
    # catch the error of cannot perform a connection to the server
    return redirect(url_for('station_detail', station_number=station_number))

key_event = None 
change_frame = False 

###################### HANDLE POST REQUEST OF KEY EVENTS FROM OPENCV ###################
@app.route('/bt1xx/update-ui/', methods=['POST'])
def update_event():
    global key_event
    global change_frame
    data = request.get_json()
    key_event = data.get('key')
    change_frame = data.get('change_frame')
    return jsonify({'success': True})

# register the endpoint
# update_key_event = GetKeyEvent()
@app.route('/bt1xx/get-updates/', methods=['GET'])
def get_key():
  global key_event
  global change_frame
  return jsonify({
    'key': key_event,
    'change_frame' : change_frame
  })

image_data = None
###################### STATION SHOW FRAME ######################
# an endpoint to handle the post request to post the frame jpeg to the server from the camera
@app.route('/bt1xx/post-frames/<int:station_number>/', methods=['POST'])
def post_frames(station_number):
  global image_data
  image_data = request.get_data()
  return jsonify({'Message' : 'Image has been sent successfully!'}), 200

# an endpoint to handle the get request to get the frame jpeg to the server
@app.route('/bt1xx/get-frames/<int:station_number>', methods=['GET'])
def get_image(station_number):
  global image_data
  if image_data is not None:
    # return the image data as a binary response
    return Response(image_data, mimetype='image/jpeg')
  else:
    # handle case where image data has not been sent
    return jsonify({'Message' : 'No image data available!'}), 401


@app.route('/bt1xx/paramSetup/showframe/station/<int:station_number>/', methods=['GET'])
@validate_token('show_frame_params')
def show_frame_params(station_number):
  # get the IP address of the connected device depends on the station number by calling the helper function
  # loop through the stations list to find the associate IP Address
  IP = partList['station' + str(station_number)]["IP"]
  name = partList['station' + str(station_number)]["name"]
  
  try:
    pipeline = createPipeline()
    print("here")
    device_info = dai.DeviceInfo(IP)
    device_info.state = dai.XLinkDeviceState.X_LINK_BOOTLOADER
    device_info.protocol = dai.XLinkProtocol.X_LINK_TCP_IP

    for device in dai.Device.getAllAvailableDevices():
      print(f"{device.getMxId()} {device.state}")

    with dai.Device(pipeline, device_info) as device:
      print(f"Ayoo! What's up!")
      global key_event
      recalibration = Recalibration(station='station' + str(station_number))
      
      # import paramSetup function to set the focal length and the brightness of the camera (camera settings)
      # brightness, lensPos = paramsSetup(station_number, captureObject, recalibrate=True, name=IP)
      recalibration.paramSetup(device, str(station_number))

      # overwrite the params.json
      this_station = 'station' + str(station_number)
      recalibration.updateJson(station=this_station)
    
    return redirect(url_for('setUpSuccessful', station_number=station_number))

  except:
    print(f"There is an error connecting to the device!")
    return redirect(url_for('station_detail', station_number=station_number))

###################### STATION CHANGE SETTINGS #################
# retrieve the data from the form
@app.route('/bt1xx/station/<int:station_number>/changeSettings', methods=['POST'])
@validate_token('change_settings')
def change_settings(station_number):
  # get the IP address of the connected device depends on the station number by calling the helper function
  IP = partList['station' + str(station_number)]["IP"]
  name = partList['station' + str(station_number)]["name"]

  if request.method == 'POST':
    try:
      # insert into the station detail table
      station_selected = station_number
      focal_length_settings = request.form['focal_length_setting_input']
      brightness_setting = request.form['brightness_setting_input']
      white_balance_lock_data = request.form['white_balance_lock_input']
      auto_exposure_lock_data = request.form['auto_exposure_lock_input']

      if white_balance_lock_data == 'false':
        white_balance_lock_data = False
      else:
        white_balance_lock_data = True

      if auto_exposure_lock_data == 'false':
        auto_exposure_lock_data = False
      else:
        auto_exposure_lock_data = True

      # create a list of new setting instance
      new_settings = [
        Station(name=name, IP_address = IP, station_number=station_selected, station_focalLength=focal_length_settings,station_brightness=brightness_setting,white_balance_lock=white_balance_lock_data, auto_exposure_lock = auto_exposure_lock_data)
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

      result = Station.query.filter_by(station_number=station_selected, IP_address=IP, name=name).first()

      if result:
        print(f"Data has been inserted successfully!")
        return redirect(url_for('setUpSuccessful', station_number=station_number))
      
      else:
        print(f"Error inserting data into the database")
        pass

    # catch the error if the requirements are not met by the database
    except:
      db.session.rollback()
      print(f"There is an error while inserting the data into the database!")
      return redirect(url_for('station_settings', station_number=station_selected))
  
  # return render_template("successful.html", station_number=station_number)

click_event = False
###################### SENDING CLICK EVENT FOR MASK SETUP #######################
@app.route('/bt1xx/handle-click/', methods=['POST'])
def handle_click():
  global click_event
  data = request.get_json()
  click_event = data.get('btnClick')
  return jsonify({'success' : True})

##################### GETTING CLICK EVENT FOR MASK SETUP #######################
@app.route('/bt1xx/getclickevent/', methods=['GET'])
def get_click():
  global click_event
  return jsonify(
    {
      'btnClick' : click_event
    }
  )

####################### STATION MASKS SETTINGS ###############
# render the url for station mask setup instructions
@app.route('/bt1xx/station/<int:station_number>/masksetup')
@validate_token('station_mask_setup')
def station_mask_setup(station_number):
  return render_template("station_masksetup.html", station_number=station_number)

# render the url for setting up the mask action
@app.route('/bt1xx/createmask/showframe/station/<int:station_number>/')
@validate_token('create_mask')
def create_mask(station_number):
  # call the function for connecting to the devices
  IP = partList['station' + str(station_number)]["IP"]
  name = partList['station' + str(station_number)]["name"]

  try:
    pipeline = createPipeline()

    device_info = dai.DeviceInfo(IP)
    device_info.state = dai.XLinkDeviceState.X_LINK_BOOTLOADER
    device_info.protocol = dai.XLinkProtocol.X_LINK_TCP_IP

    for device in dai.Device.getAllAvailableDevices():
      print(f"{device.getMxId()} {device.state}")

    with dai.Device(pipeline, device_info) as device:
      recalibration = Recalibration(station='station' + str(station_number))
      recalibration.upDateParams(station='station' + str(station_number))
      recalibration.adjustCamera(device=device)
      recalibration.maskSetup(device=device)

    return redirect(url_for('setUpSuccessful', station_number=station_number))

  except:
    print(f"Error connecting to the device!")
    return redirect(url_for('station_detail', station_number=station_number))
  
part100 = ['--select--']
part120 = ['--select--']
# read in params.json file for the parts
with open('params.json', 'r') as f:
  partList = json.load(f)

params100 = partList['station100']['parts'] # get the part list for station 100
params120 = partList['station120']['parts'] # get the part list for station 120

for i in params100:
  part100.append(i)

for j in params120:
  part120.append(j)

################ REDO MASK URL ################
# this function will render the redo mask url
@app.route('/bt1xx/redo-mask/<int:station_number>')
@validate_token('redo_mask')
def redo_mask(station_number):
  return render_template('redo-mask.html', station_number=station_number, errors={}, mask_options_100=part100, mask_options_120=part120)

############### HANDLE REDO MASK REQUEST ###########
# this function will handle the post request to redo the mask
@app.route('/bt1xx/handle-redo-mask/<int:station_number>/', methods=['POST'])
@validate_token('handle_redo_mask')
def handle_redo_mask(station_number):
  if request.method == 'POST':
    # call the function for connecting to the devices
    IP = partList['station' + str(station_number)]["IP"]
    name = partList['station' + str(station_number)]["name"]

    # get the form input
    part_chosen = request.form['mask_options_id']
    errors = {}

    # validate the form input
    if (part_chosen == '--select--'):
      errors['mask_options_id'] = f'You have to choose the part you want to redo the mask!'
      return render_template('redo-mask.html', station_number = station_number, errors=errors, mask_options_100=part100, mask_options_120=part120)

    # get the index of the chosen part
    if station_number == 100:
      for i in range(len(part100)):
        if(part_chosen == part100[i]):
          part_chosen_index = i
          break
      part_chosen_index -= 2
    else:
      for i in range(len(part120)):
        if(part_chosen == part120[i]):
          part_chosen_index = i
          break
      part_chosen_index -= 2

  try:
    pipeline = createPipeline()

    device_info = dai.DeviceInfo(IP)
    device_info.state = dai.XLinkDeviceState.X_LINK_BOOTLOADER
    device_info.protocol = dai.XLinkProtocol.X_LINK_TCP_IP

    for device in dai.Device.getAllAvailableDevices():
      print(f"{device.getMxId()} {device.state}")

    with dai.Device(pipeline, device_info) as device:
      recalibration = Recalibration(station='station' + str(station_number))
      recalibration.upDateParams(station='station' + str(station_number))
      recalibration.redo_mask(device, part_chosen_index, part_chosen)
  
    return redirect(url_for('setUpSuccessful', station_number=station_number))

  except:
    print(f"Error connecting to the device!")
    return redirect(url_for('station_mask_setup', station_number=station_number))
    
############################### STATION ERRORS SETUP PAGE ######################
@app.route('/bt1xx/station/<int:station_number>/errorsetup')
@validate_token('station_errors_setup')
def station_errors_setup(station_number):
  return render_template("station_errorsetup.html", station_number=station_number)

# render the url for setting up errors actions
@app.route('/bt1xx/errors/showframe/station/<int:station_number>')
@validate_token('create_errors')
def create_errors(station_number):
  # call the function to connect to a device
  IP = partList['station' + str(station_number)]["IP"]
  name = partList['station' + str(station_number)]["name"]

  try:
    pipeline = createPipeline()

    device_info = dai.DeviceInfo(IP)
    device_info.state = dai.XLinkDeviceState.X_LINK_BOOTLOADER
    device_info.protocol = dai.XLinkProtocol.X_LINK_TCP_IP

    for device in dai.Device.getAllAvailableDevices():
      print(f"{device.getMxId()} {device.state}")

    with dai.Device(pipeline, device_info) as device:
      # call a function to set up the errors
      recalibration = Recalibration(station='station' + str(station_number))
      recalibration.upDateParams(station='station' + str(station_number))
      recalibration.adjustCamera(device=device)
      recalibration.pressKeyCapture(device=device, path=recalibration.standardPath)
      recalibration.errorSetup(device=device)
      recalibration.updateJson(station='station' + str(station_number))

    return redirect(url_for('setUpSuccessful', station_number=station_number))

  except:
    print(f"Error connecting to the device!")
    return redirect(url_for('station_detail', station_number=station_number))

################ SUCCESSFUL PAGE AFTER SETTING UP #################
@app.route('/bt1xx/station_settings/<int:station_number>/successful/')
@validate_token('finish_setup')
def setUpSuccessful(station_number):
  return render_template('successful.html', station_number=station_number)

################################# LOG IN PAGE #############################
# render the login page for non-admin users
@app.route('/bt1xx/login/')
def login():
  return render_template('login.html')

# authenticate the users login
@app.route('/bt1xx/authentication/', methods=['POST'])
def authentication():
  # if the user is not in session then abort the users to not authorized url
  if request.method == 'POST':
    try:
      username = request.form['username']
      password = request.form['password']
      # initiate an error dictionary to catch any error
      errors = {}

      # validate the user's input before sending as a POST request
      if len(username) == 0:
        errors['username'] = f"Please enter your username!"

      if len(password) == 0:
        errors['password'] = f"Please enter your password!"

      # query the user record from the database
      query = {
        "username" : username
      }

      user = mongo_db.Users.find_one(query)
      # validate the user credentials
      if user is not None:
        # user = json_util.dumps(user)
        # user = json_util.loads(user)
        # if the user is admin -> query mysql database to get the admin information
        admin_user = Users.query.filter_by(username=user['username']).first()
        # if the username and password are found in the database and is admin
        if admin_user:
          if bcrypt.checkpw(password.encode('utf-8'), admin_user.password.encode('utf-8')):
            # User credentials are valid
            # Generate JWT token and store it in cookies
            # query the permissions list in the user table with the user id
            permissions = [permission.name for permission in admin_user.permissions]
            token = jwt.encode({'id' : admin_user.id, 'name' : admin_user.name,  'username' : admin_user.username, 'exp': datetime.now(pytz.timezone('EST')) + timedelta(minutes=60), 'permissions' : permissions}, app.config['SECRET_KEY'], algorithm='HS256')

            # Store the token in a cookie
            response = make_response(redirect(url_for('homepage')))
            response.set_cookie('token', value=token, expires=datetime.now(pytz.timezone('EST')) + timedelta(minutes=60), httponly=True)

            # Redirect the user to the homepage and some restricted resources
            return response
          
        else: # if the user is not admin
          if bcrypt.checkpw(password.encode('utf-8'), user['password']):
            # User credentials are valid
            # Generate JWT token and store it in cookies
            # query the permissions list in the user table with the user id
            permissions = []
            for i in range(len(user['permissions'])):
              permissions.append(user['permissions'][f'permission{i}']['permission_name'])
            token = jwt.encode({'id' : user['id'], 'name' : user['name'],  'username' : user['username'], 'exp': datetime.now(pytz.timezone('EST')) + timedelta(minutes=60), 'permissions' : permissions}, app.config['SECRET_KEY'], algorithm='HS256')

            # Store the token in a cookie
            response = make_response(redirect(url_for('homepage')))
            response.set_cookie('token', value=token, expires=datetime.now(pytz.timezone('EST')) + timedelta(minutes=60), httponly=True)

            # Redirect the user to the homepage and some restricted resources
            return response
            
      else:
        errors['username'] = f"Sorry! You are not authorized for this program!"
        raise ValueError
 
    except BaseException:
      return render_template('login.html', errors=errors)

# If the user chooses to log out the program
@app.route('/bt1xx/logout/')
def logout():
  # get the token from cookies
  token = request.cookies.get('token')
  # set the token to be expired
  response = make_response(redirect(url_for('login')))
  response.set_cookie('token', value=token, expires=0, httponly=True)
  return response
  
############################## RUNNING ALL THE PROGRAMS ##############################
data = None
# a server to handle the GET request to get all the numbers of the cameras that are running
@app.route('/bt1xx/post-all-cameras/', methods=['POST'])
def post_all_cameras():
  if request.method == 'POST':
    # get the data from the request body
    try:
      global data
      data = request.get_json()
      print(data)
      return jsonify({
        'message' : 'The number of cameras that are running has been received successfully!',
        'data' : data
      }), 200
    # try to catch if there is any error with the server
    except Exception as error:
      print(error)
      return jsonify(response_data  = ({
        'message' : f'There is an internal server error while getting the data from the POST request: {error}'
      })), 500

@app.route('/bt1xx/get-all-cameras/', methods=['GET'])
def get_all_cameras():
  if request.method == 'GET':
    try:
      global data
      return jsonify({
        'cameras' : data
      }), 200
    except Exception as error:
      # try to catch all the errors
      return jsonify({
        'message' : f'There is an internal server error while getting the number of cameras: {error}'
      }), 500

@app.route('/bt1xx/startallprograms/', methods=['POST','GET'])
@validate_token('run_cameras')
def startPrograms():
  try:
    # finish the GET request before running all the cameras
    post_all_cameras_url = 'http://127.0.0.1:5000/bt1xx/post-all-cameras/'

    # send a GET request to the server to send the number of cameras are running
    request_headers = {
      'Content-Type' : 'application/json'
    }

    request_data = {
      "cameras" : 2,
      "station_cam" : {
        '1' : '120',
        '2' : '100',
      }
    }

    request_json = json.dumps(request_data)

    response = requests.post(url=post_all_cameras_url, headers=request_headers, data=request_json)
    print(response.status_code)

    if response.status_code == 200:
      print(f'Request has been sent to the server successfully')
    
    else:
      raise ValueError
    
  # catch the error
  except ValueError as error:
    response_data = ({
      'message' : f'There is an error with running all the cameras: {error}',
      'status_code' : 500
    })
    # send the request along with the data to the server
    response = requests.post(url=post_all_cameras_url, data=response_data)
    return response
  
  # run all the cameras files
  run_all_cameras()
  return render_template('view.html')


result_data = None
######################### APIs to handle POST and GET request of the data when running the cameras #########################
@app.route('/bt1xx/post-result/<int:station_number>/', methods=['POST'])
def post_result(station_number):
  if request.method == 'POST': # handle the POST request
    try:
      global result_data
      # get the result data
      result_data = request.get_json()
      print(result_data)
      return jsonify({
        'message' : 'Successfully receive the data from the POST request!',
        'result_data' : result_data
      }), 200
    except Exception as error: # get the error and display
      print(error)
      return jsonify({
        'message' : f'There is an internal server error when handling the POST request: {error}'
      }), 500
    
@app.route('/bt1xx/get-result/<int:station_number>/', methods=['GET'])
def get_result(station_number):
  if request.method == 'GET': # handle the GET request
    try:
      global result_data
      return jsonify({
        'get_data' : result_data
      }), 200
    except Exception as error:
      # get and display the error
      print(error)
      return jsonify({
        'message' : f'Catch an error while handling the GET request: {error}'
      }), 500

@validate_token(permission='can_insert_user') # only admin users can access this API
@app.route('/bt1xx/insert-users/', methods=['GET'])
def insert_new_users():
  # read in the users.json
  with open('users.json', 'r') as f:
    users = json.load(f)

  try:
    for i in range(6):
      user_uuid = uuid.uuid4()
      users[f"user{i}"]["id"] = str(user_uuid) # change the id to UUID
      # validate the user's password to see if it meets the requirements
      if users[f"user{i}"]["password"] == users[f"user{i}"]["username"] and len(users[f"user{i}"]["password"]) < 8 and not any(char.isupper() for char in users[f"user{i}"]["password"]) and not any(char in '!@#$%^&*' for char in users[f"users{i}"]["password"]):
        return jsonify({
          'message' : "Password does not meet the requirements!"
        }), 400
      
      # query mongodb database to see if the username or password already existed
      f_query = {
        "name" : users[f"user{i}"]["name"],
        "username" : users[f"user{i}"]["username"]
      }

      f_user = mongo_db.Users.find(f_query)

      # if either the username nor the password has existed in the database yet
      if f_user.count()==0:
        if validate_username(username=users[f"user{i}"]["username"]):
          salt = bcrypt.gensalt()
          # hash the password using bcrypt hashing algorithm
          hashed_password = bcrypt.hashpw(users[f"user{i}"]["password"].encode('utf-8'), salt)
          users[f"user{i}"]["password"] = hashed_password # hashed the password
        else:
          raise ValueError
        mongo_db.Users.insert_one((users[f"user{i}"])) # insert the user into mongodb
      else:
        return jsonify({
          'message' : "This username or password already existed in the database!",
          "found_user" : json_util.dumps(list(f_user)) # if found the users with the same username or password
        }), 409

    # if all the data has been inserted successfully
    response_data = ({
      'message' : "All users have been inserted successfully"
    })
    response_json = json.dumps(response_data)
    response = Response(response_json, status=HTTPStatus.CREATED, mimetype='application/json')
    return response
  
  except Exception or ValueError as error:
    response_data = ({
      'message' : f'There is an internal server error while inserting user into the database: {error}'
    })
    print(error)
    response_json = json.dumps(response_data)
    response = Response(response_json, status=500, mimetype="application/json")
    return response
  
# a route for users to change their password
@validate_token('can_insert_user')
@app.route('/bt1xx/users/change-password/', methods=['GET'])
def update_password_form():
  if request.method == 'GET':
    return render_template('change_password_user.html')

@validate_token('can_insert_user')
@app.route('/bt1xx/users/handle-change-password/', methods=['POST'])
def handle_update_password():
  if request.method == 'POST':
    try:
      username = request.form['username']
      new_password = request.form['new-password']
      new_password_confirmation = request.form["new-password-confirmation"]

      # create an errors dictionary
      errors = {}

    
      # find the user with the username in the database
      f_username_query = {
        'username' : username
      }

      f_username = mongo_db.Users.find(f_username_query)

      if f_username.count() == 0: # no username found in the database
        errors['username'] = 'No username found!'
        return render_template('change_password_user.html', erorrs=errors)

      # new_password and new_password_confirmation
      if new_password == username and len(new_password) < 8 and not any(char.isupper() for char in new_password) and not any(char in '!@#$%^&*' for char in new_password):
        errors['new-password'] = "New password does not meet our requirements!"
        return render_template('change_password_user.html', erorrs=errors)
      
      if new_password != new_password_confirmation:
        errors['new-password-confirmation'] = "New password confirmation and new password does not match each other!"
        return render_template('change_password_user.html', erorrs=errors)

      # hashed the new password

      
      # run a migration to MongoDB to update the new password for the username
      migration = mongo_db.Users.update_one(
        f_username_query,
        {
          "$set" : {
            "password" : new_password
          }
        }
      )
      
      print(migration.modified_count, f"user with username: {username} is updated")
      return jsonify({
        'message' : 'Successfully update the user password'
      }), 201
    
    except Exception as error: # catch any server-side error
      return jsonify({
        'message' : f"There is an internal server error while updating user's password: {error}"
      }), 500

if __name__ == '__main__':
 # connect to the websocket server to listening for events sent from localhost:5000
 app.run(debug=True)








