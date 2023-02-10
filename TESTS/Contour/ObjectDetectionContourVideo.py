import cv2
import numpy as np
import matplotlib.pyplot as plt

#Load video
video = cv2.VideoCapture('PXL_20230210_210347789.mp4')
#Array of numerical co-efficents for pixels in an image. None is default 3x3 size.
kernel = None

#Initialize background object
#Detect shadows seperates entities from their shadows so objects with overlapping shadows do not count as 1, is not visual.
BackgroundObject = cv2.createBackgroundSubtractorMOG2(detectShadows = True)

while(video.isOpened()):
    ret, frame = video.read()
    if not ret:
        break
    else:
        #Apply the background object on the frame to get the segmented mask.
        fgmask = BackgroundObject.apply(frame)

        #Since shadows are masked as grey and objects as white. We can set threshold to ignore grey.
        _ , fgmask = cv2.threshold(fgmask, 300, 455, cv2.THRESH_BINARY)

        #Dilation increases white area of figures
        #Erode increases black area of mask
        fgmask = cv2.erode(fgmask, kernel, iterations = 1)
        fgmask = cv2.dilate(fgmask, kernel, iterations = 2)

        #Define Contours
        contours, _ = cv2.findContours(fgmask, cv2. RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        #Input boxes around objects
        frameCopy = frame.copy()

        for cnt in contours:

        #Raise threshold detection area
            if cv2.contourArea(cnt) > 10000:

                # Retrieve the bounding box coordinates from the contour.
                x, y, width, height = cv2.boundingRect(cnt)
            
                # Draw a bounding box.
                cv2.rectangle(frameCopy, (x , y), (x + width, y + height),(0, 0, 255), 2)
            
                # Write Detected near the bounding box drawn.
                cv2.putText(frameCopy, 'Object Detected', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0,255,0), 1, cv2.LINE_AA)
    
        # Extract the foreground from the frame using the segmented mask.
        foregroundPart = cv2.bitwise_and(frame, frame, mask=fgmask)
        
        # Stack the original frame, extracted foreground, and annotated frame. 
        stacked = np.hstack((frame, foregroundPart, frameCopy))

        # Display the stacked image with an appropriate title.
        cv2.imshow('Original Frame, Extracted Foreground and Detected Object', cv2.resize(stacked, None, fx=0.5, fy=0.5))
        #cv2.imshow('initial Mask', initialMask)
        #cv2.imshow('Noisy Mask', noisymask)
        #cv2.imshow('Clean Mask', fgmask)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
        
video.release()
cv2.destroyAllWindows()
