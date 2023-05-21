# Winter Workterm 2023 - Parts Present Detection Project

### What we do?

+ Main program:
  - DepthAI cameras are using for connecting to our computer vision program.
  - Our program is mainly written in Python with OpenCV dependency for processing the images that were sent from the cameras.
  - We are currently testing our program at 2 stations at Martinrea Hydroform Solution!
  - The program is designed to reduce the needs for sensors installation to detect the presence of the object at the stations.

+ Full-stack web application:
  - A website is designed for the users to interact with the computer vision program.
  - Provides a user-friendly way for viewing the output of the program and interacting with the cameras.

### Our process:

+ Main program:
  - Technical: [Python OpenCV](https://pypi.org/project/opencv-python/)
  - Connecting DepthAI cameras through Ethernet cables using DepthAI open-source dependencies.
  - An image of a silver part, an image of a colour part and a normal image are taken and sent to the computer for image processing.
  - By using our developed algorithm, we can generate a mask that contains the difference between the two images which is also the region of that cover the part. 
  - Another Mean Square Algorithm (MSE) came in for calculating the difference between the mask image (which we generated above) and the normal image to account for the determination of the program that whether the part is presenced or not.
  - The last algorithm that we developed is using for determining the PASS/FAIL rate based on the MSE output and send it to the PLC.
  - Scale the process up for multiple cameras on multiple stations

+ Website:
  - Front-end (UI/UX):
    * Techincal: HTML, CSS and JavaScript ([Werkzeug](https://werkzeug.palletsprojects.com/en/2.2.x/) and [Jinja Template](https://jinja.palletsprojects.com/en/3.1.x/)) built-in templates for user-interface.
    * Design and develop a user-friendly webpages for the users to easily change the configuration of the cameras (change settings, create mask process,...).
    * Render the frames of the cameras for on the iframe for users to easily track their change to the cameras.
  
  - Backend (Web Security Practice and trigger with the computer vision program)
    * Technical: [JavaSript](https://nodejs.org/en/download/), [Python Flask](https://flask.palletsprojects.com/en/2.2.x/), HTTP and Restful API.
    * Bulding Flask routes to trigger all Python functions in our main program.
    * Protect the users from security risk by using API Security Practice.
    * Fetch and Rest API to listen for request and response from JavaScript client to Python server for events from the user-interface.
    
### DEMO:
Here are a few demo images of what we have so far:
![Our mask demo](https://github.com/Kenttrann2302/Object-Detection/blob/main/backend/Photos/Masks/station100/top.jpg?raw=true)


![Our architecture demo]()

<img width="744" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/c388fa0e-545a-46e0-8109-412fc170b24a">


![Our website demo]()

- Our login page:

<img width="856" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/c4c9620a-5d67-4524-8588-eac500fba539">

- Our homepage:

<img width="903" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/d95a7f73-83b1-456c-b935-71671b1ccecb">

- Our demo dashboard for station 100:

<img width="876" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/3405572a-81c7-4301-8fe8-c74d5c028513">

<img width="860" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/c17979c0-72d0-407f-ae5f-283df1435cc5">

<img width="860" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/434007d3-180e-4e49-9520-c02028863fa4">

<img width="864" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/4ddb623e-360e-4161-b9e6-4dfc3ab8b6c1">

- Setting configurations for our cameras as well as mask set up, redo the mask for a certain part and our algorithm setup:

<img width="858" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/3c566157-2d0f-4bac-91d7-ef0964202414">

<img width="858" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/9af44787-d1c1-454f-85d0-e3c7b1d26c6e">

<img width="858" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/15cdb31a-01bd-4dfd-8ad8-0fb5e60e5343">

<img width="852" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/454783f3-d79c-401c-94b3-91b327026d9d">


![Some output demo]()

<img width="854" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/c4fbea85-7a7f-4042-9078-0d5046189f94">

<img width="854" alt="image" src="https://github.com/Kenttrann2302/Object-Detection/assets/110959350/9816c02f-b9a3-4982-a307-cc02d1486723">
  
  
## Requirements for development and contribution:

- [Python 3.9 to 3.11.1](https://www.python.org/downloads/release/python-3111/) is required.
- [OpenCV Python (4.7.0)](https://pypi.org/project/opencv-python/) installation.
- [Python Flask (2.2.3)](https://pypi.org/project/Flask/) installation
- [DepthAI](https://docs.luxonis.com/projects/api/en/latest/install/) installation.
- [NodeJS 16](https://nodejs.org/en/download/) is required.
- Other dependencies are covered in requirements.txt files.

### Local Development:

```
# Clone the repo
$ git clone https://github.com/Kenttrann2302/Object-Detection/

# Move into directories 
$ cd <directory-name>

# Install the requirements to run the program
$ cd backend
$ cd txt_files
$ pip install -r requirements1.txt

# Start the program on bash and have fun!!!
$ python cam1.py & cam2.py (assume 2 cameras are installed)
```
```
# How to start local development server on http://localhost:5000/
# Install virtual environment on local machine
# Unix/MacOS:
$ python3 -m venv env

# Window:
> py -m venv env

# Activating the a virtual environment
# Unix/MacOS:
$ cd backend
$ source myenv/bin/activate

# Windows:
> cd backend
> .\myenv\Scripts\activate

# Installing the packages in virtual environment
# For both Windows and Unix/MacOS
$ cd txt_files
$ pip install -r requirements1.txt

# Start the server that listening on port 5000
# change directory back to the root directory
$ python app.py

# To deactivate the virtual environment
# For both Windows and Unix/MacOS:
$ deactivate

# Note: For best experience, enable Flask debugging mode for local development and disable for production due to security risks.
```

