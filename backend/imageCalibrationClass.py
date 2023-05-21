# a class that apply all the methods on the camera 
import json
import depthai as dai
import cv2 as cv
import time
from imageMaskGeneration import createMask
from imageProcessingClasses import imageProcessing
from imagePredictionClass import getPassRef
import requests

# this function is responsible for creating the pipeline that is connected the machine to the camera
def createPipeline():
    pipeline = dai.Pipeline()
    # This might improve reducing the latency on some systems
    pipeline.setXLinkChunkSize(0)

    # Define source and output
    camRgb = pipeline.create(dai.node.ColorCamera)
    camRgb.setFps(3)
    camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
    camRgb.setPreviewSize(1920, 1080)

    xout = pipeline.create(dai.node.XLinkOut)
    xout.setStreamName("out")
    xin = pipeline.create(dai.node.XLinkIn)
    xin.setStreamName("control")
    xin.out.link(camRgb.inputControl)
    camRgb.isp.link(xout.input)
    return pipeline

def clamp(num, v0, v1):
    return max(v0, min(num, v1))

# camera's set up contains: set up the camera settings (focal length, brightness), mask setup process, redo mask setup process and set up the errors algorithm for the camera
class Recalibration:
    def __init__(self, station) -> None:
        with open (r'params.json') as f:
              partList = json.load(f)
              
        # select which station to use here
        # all the values associate with the camera and the station
        self.station = station
        params = partList[station]
        self.passref = params["passref"]
        self.brightness = params["brightness"]
        self.lensPos = params["lensPos"]
        self.parts = params["parts"]
        self.IP = params["IP"]
        self.name = params["name"]
        self.maskPaths = params["masks"]
        self.refPaths = params["refs"]
        self.colPaths = params ["cols"]
        self.standardPath = params["standard"]
        self.testPath = params["test"]
    
    # this function setup params for stations (focal length, brightness, white balance lock, auto exposure lock)
    def paramSetup(self, device, stationNumber):
        # push the device into the queue
        q = device.getOutputQueue(name="out")
        qControl = device.getInputQueue(name="control")
        
        # the idea here is in order to establish the interaction between the Python (server - where the camera's program is running) and JavaScript (client), we need to use JavaScript to detects the key press on the client side and send it as a HTTP request to the Python server, here, Python will perform a GET request to the Python server to get the key pressed and update the camera's params accordingly.

        # the idea would be the same for Python to send the decoded image to the Python server whenever the new frame is updated, then JavaScript will act like a client to perform a GET request from the Python server to get the frame and update it accordingly on the iframe element
        # the url server to send the frame of the camera to 
        url = 'http://127.0.0.1:5000/bt1xx/post-frames/' + stationNumber + '/'
        headers = {
            'Content-Type' : 'image/jpeg'
        }

        # send the GET request to '/bt1xx/get-updates/' url server to get the key event
        key_url = 'http://127.0.0.1:5000/bt1xx/get-updates/'
        # send the POST request to '/bt1xx/update-ui/' url server to change the frame and key event after the user pressed on the client side
        update_key_url = 'http://127.0.0.1:5000/bt1xx/update-ui/'

        while True:
            # get the frame from the queue
            frame = q.get().getCvFrame()
            frame = cv.pyrDown(frame)

            cv.imshow(self.station, frame)
            
            key_code = cv.waitKey(1) # wait for the key to be pressed if the focus is on the PyLauncher Window

             # send the frame to the server, perform the request to the server to see if the key event has been detected
            key_response = requests.get(key_url)
            if key_response.status_code == 200 and key_response.json() is not None:
                change_frame = key_response.json().get('change_frame')
                get_key = key_response.json().get('key')
            
            else: 
                print(f"There is an error while getting the key event from the server with status code: {response.status_code}")
                pass

            # brightness adjustment, get_key is the value of the key that was being sent after making a GET request from the key_url
            if key_code in [ord(','), ord('.')] or get_key == ',' or get_key == '.':
                if key_code == ord(',') or get_key == ',':  
                    self.lensPos -= 2
                elif key_code == ord('.') or get_key == '.':
                    self.lensPos += 2
                self.lensPos = clamp(self.lensPos, 0, 255)
                print("Setting manual focus, lens position: ", self.lensPos)
                ctrl = dai.CameraControl()
                ctrl.setManualFocus(self.lensPos)
                qControl.send(ctrl)
            

            # focal length adjustment, get_key is the value of the key that was being sent after making a GET request from the key_url    
            elif key_code in [ord('k'), ord('l')] or get_key == 'k' or get_key == 'l':
                if key_code == ord('k') or get_key == 'k':
                    self.brightness -= 1
                elif key_code == ord('l') or get_key == 'l':
                    self.brightness += 1
                self.brightness = clamp(self.brightness, -10, 10)
                print("Brightness:", self.brightness)
                ctrl = dai.CameraControl()
                ctrl.setBrightness(self.brightness)
                qControl.send(ctrl) 
            
            # if the key pressed is "q" then we destroy the frame and save the settings for the camera
            if key_code == ord('q') or get_key == 'q':
                return 
            
            # convert the frame to JPEG format
            _, buffer = cv.imencode('.jpg', frame)
            if change_frame == True:
                # send a POST request to the server along with the decoded frame 
                response = requests.post(url, data=buffer.tobytes(), headers=headers)
                if response.status_code == 200:
                    print('Frame uploaded successfully')
                    # send back a post request to let the server knows that we don't need to update a frame anymore since the key is not being pressed
                    new_response = requests.post(update_key_url, json={ # Fix this to PATCH request instead of POST request
                        'change_frame' : False,
                        'key' : 'a'
                    })
                    if new_response.status_code == 200:
                        change_frame = False # get out of the loop
                else: 
                    print('Error uploading frame:', response.status_code)
            
    
    # this function setup masks for station
    def maskSetup(self, device):
        # the idea here is going to be the same as the paramSetup function, we send a GET and POST request to the server in order to get the button clicked from JavaScript POST FETCH API to let the program knows that the part has been loaded and the picture for generating the mask can be captured now
        q = device.getOutputQueue(name="out")
        i = 0           
        get_url = 'http://127.0.0.1:5000/bt1xx/getclickevent/'
        post_url = 'http://127.0.0.1:5000/bt1xx/handle-click/'

        click = None

        while i < len(self.parts):
            print("load"+ self.parts[i] + "silver part and press c to capture")
            while True:
                imgSil = q.get().getCvFrame()

                # send the GET request to '/bt1xx/getclickevent/' url server to get the response which boolean of the btn clicked 
                response = requests.get(get_url)
        
                if response.status_code == 200:
                    try:
                        print('Detect a button clicked!')
                        click = response.json().get('btnClick') 
                    except json.decoder.JSONDecodeError:
                        pass

                key = cv.waitKey(1)
                if key == ord('c') or click == True:
                    cv.imwrite(self.refPaths[i], imgSil)
                    cv.destroyAllWindows()
                    # send the POST request to '/bt1xx/handle-click/' url server to update the btn click (fix this to PUT request)
                    new_response = requests.post(post_url, json={
                        'btnClick' : False
                    })
                    if new_response.status_code == 200:      
                        break
                imgSil = cv.pyrDown(imgSil)
                cv.imshow("results", imgSil)
                
            print("load"+ self.parts[i] + "colour part and press c to capture. If the part lies below others, load those as well")
            while True:
                imgCol = q.get().getCvFrame()

                # send the GET request to '/bt1xx/getclickevent/' url server to get the response
                response = requests.get(get_url)

                if response.status_code == 200:
                    click = response.json().get('btnClick')

                key = cv.waitKey(1)
                if key == ord('c') or click == True:
                    cv.imwrite(self.colPaths[i], imgCol)
                    cv.destroyAllWindows()
                    # send the POST request to '/bt1xx/handle-click/' url server to update the btn click (fix this to PUT request)
                    new_response = requests.post(post_url, json={
                        'btnClick' : False
                    })
                    if new_response.status_code == 200:      
                        break
                imgCol = cv.pyrDown(imgCol)
                cv.imshow("results", imgCol)
            print("Creating a mask, this may take a minute")
            if createMask(imgSil, imgCol, self.maskPaths[i]):
                i += 1
                print("Mask generated")
                # send a post request towards 
            else:
                print(f"Mask failed. Retrying")
        
        print("all masks are done")
        return
    
    # function receive the redo mask command
    def redo_mask(self, device, part_number, part): # part number is the associate index of the part in the array
        q = device.getOutputQueue(name="out")
        i = 0

        url = 'http://127.0.0.1:5000/bt1xx/getclickevent/'
        post_url = 'http://127.0.0.1:5000/bt1xx/handle-click/'
        
        # load the silver part
        print("Load" + part + "silver part and press C to capture. If the part lies below others, load those as well.")
        while True:
            imgSil = q.get().getCvFrame()

            # send the GET request to '/bt1xx/getclickevent/' url server to get the response
            response = requests.get(url)

            if response.status_code == 200:
                click = response.json().get('btnClick')

            key = cv.waitKey(1)
            if key == ord('c') and click == True:
                cv.imwrite(self.refPaths[part_number], imgSil)
                cv.destroyAllWindows()
                # send the POST request to '/bt1xx/handle-click/' url server to update the btn click (fix this to PUT request)
                new_response = requests.post(post_url, json={
                    'btnClick' : False
                })
                if new_response.status_code == 200:      
                    break
            imgSil = cv.pyrDown(imgSil)
            cv.imshow("results", imgSil)

        print("Load" + part + "colour part and press C to capture. If the part lies below others, load those as well")
        while True:
            imgCol = q.get().getCvFrame()

            # send the GET request to '/bt1xx/getclickevent/' url server to get the response
            response = requests.get(url)

            if response.status_code == 200:
                click = response.json().get('btnClick')

            key = cv.waitKey(1)
            if key == ord('c') and click == True:
                cv.imwrite(self.colPaths[part_number], imgCol)
                cv.destroyAllWindows()
                # send the POST request to '/bt1xx/handle-click/' url server to update the btn click (fix this to PUT request)
                new_response = requests.post(post_url, json={
                    'btnClick' : False
                })
                if new_response.status_code == 200:      
                    break
            imgCol = cv.pyrDown(imgCol)
            cv.imshow("results", imgCol)
        print("Creating a mask, this may take a minute")
        if createMask(imgSil, imgCol, self.maskPaths[part_number]):
            print("Mask generated")
    
        print(f"Redoing mask for {part} is done")
        return
    
    # this method read all the parameters from the json again                
    def upDateParams(self, station):

        with open (r'params.json', 'r') as f:
              partList = json.load(f)
              
        # select which station to use here
        params = partList[station]
        self.brightness = params["brightness"]
        self.lensPos = params["lensPos"]
        return
    
    # this function updates all the values in the json
    def updateJson(self, station):
        with open(r'params.json', 'r') as f:
            partList = json.load(f)
        
        # change the settings in json
        partList[station]["brightness"] = self.brightness
        partList[station]["lensPos"] = self.lensPos
        partList[station]["passref"] = self.passref
        
        with open('params.json', 'w') as f:
            json.dump(partList, f, indent = 4)

        print(f"Json updated")
    
    # this function set up the passref for the parts  
    def errorSetup(self, device):
        q = device.getOutputQueue(name="out")
        processingObject = imageProcessing(self.station)
        self.passref = [0]*len(self.parts)
        
        print("setting up pass references")
        for i in range(50):
            imgFrame = q.get().getCvFrame()
            processingObject.setTestImg(imgFrame)
            error = processingObject.compareImage()
            self.passref = getPassRef(error, self.passref)  
        return
    
    # this function should be called when the camera get turned on
    # it will adjust the camera to the brightness and lensPos 
    def adjustCamera(self, device):
        
        q = device.getOutputQueue(name="out")
        qControl = device.getInputQueue(name="control")
        
        print("Setting manual focus, lens position: ", self.lensPos)
        ctrl = dai.CameraControl()
        ctrl.setManualFocus(self.lensPos)
        qControl.send(ctrl)
        
        print("Brightness:", self.brightness)
        ctrl = dai.CameraControl()
        ctrl.setBrightness(self.brightness)
        qControl.send(ctrl)
        
        startTime = time.time()
        while ((time.time()-startTime) < 10):
            imgFrame = q.get().getCvFrame()
            imgFrame = cv.pyrDown(imgFrame)
            cv.imshow("adjusting the camera", imgFrame)
            cv.waitKey(1)
        
        # auto white balance lock
        print("auto white balance lock")
        ctrl = dai.CameraControl()
        ctrl.setAutoWhiteBalanceLock(True)
        qControl.send(ctrl)

        # auto exposure lock
        print("auto exposure lock")
        ctrl = dai.CameraControl()
        ctrl.setAutoExposureLock(True)
        qControl.send(ctrl)
        
        cv.destroyAllWindows()
        return
        
    # this function capture an image and return it    
    def capture(self, device):
        q = device.getOutputQueue(name="out")
        imgFrame = q.get().getCvFrame()
        return imgFrame

    # this function stream the frames until the user press c to capture an image
    def pressKeyCapture(self, device, path):
        q = device.getOutputQueue(name="out")
        
        while True:
            imgFrame = q.get().getCvFrame()
            key = cv.waitKey(1)
            if key == ord('c'):
                cv.imwrite(path, imgFrame)
                cv.destroyAllWindows()
                break
            
            imgFrame = cv.pyrDown(imgFrame)
            cv.imshow("results", imgFrame)