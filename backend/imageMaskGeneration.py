import cv2 as cv
import numpy as np
import os
import pdb


#------------------------------------------------------------------------------------------------#
#Repairs a broken mask by filling the spaces between white pixels up to a distance of 10 pixels either horizonatlly or vertically
def fillByLine(img, direction):
  if direction == "H":
    for row in range(img.shape[0]):
      start, stop = 0, 0
      for col in range(img.shape[1]):
        if img[row,col] != 0 and start == 0: 
          start = col, row
        if img[row ,col] != 0: 
          stop = col, row
      
        if start != 0 and np.abs(start[0]-stop[0]) <= 100: #MAX AMOUNT TO FILL
            cv.line(img, start, stop, 255, 1)
            start=stop
        elif start!= 0 and np.abs(start[0]-stop[0]) > 100:
          start=stop

  if direction == "V":
    for col in range(img.shape[1]):
      start, stop = 0, 0
      for row in range(img.shape[0]):
        if img[row,col] != 0 and start == 0: 
          start = col, row
        if img[row ,col] != 0: 
          stop = col, row
      
        if start != 0 and np.abs(start[1]-stop[1]) <= 100: #MAX AMOUNT TO FILL
            cv.line(img, start, stop, 255, 1)
            start=stop
        elif start!= 0 and np.abs(start[1]-stop[1]) > 100:
          start=stop
    
  return img 

#Repairs a mask by floodfilling enclosed spaces with white pixels
def floodFill(imgThresh):
  fillMask = imgThresh.copy()
  height, width = imgThresh.shape[:2]
  mask = np.zeros((height+2,width+2),np.uint8)
  cv.floodFill(fillMask, mask,(0,0),(255,255,255))
  fillMask = cv.bitwise_not(fillMask)

  return cv.add(imgThresh, fillMask)

#------------------------------------------------------------------------------------------------#

  #function to create a mask 
def createMask(std, col, maskPath):
  #Creating ref image (black image of the same size) that can be drawn on later
  ref = cv.cvtColor(std, cv.COLOR_BGR2GRAY)
  ref[ref != 0] = 0
  __, ref = cv.threshold(ref, 0, 255, cv.THRESH_BINARY)

  #Image subtraction
  diff = cv.absdiff(std, col)

  #Denoising
  denoise = np.float32(diff) / 255.0
  kernel_size = 3
  blur = cv.GaussianBlur(denoise, (kernel_size, kernel_size),0)
  denoise = np.uint8(blur * 255)

  #Convert to gray
  gray = cv.cvtColor(denoise, cv.COLOR_BGR2GRAY)

  #Perform morphological transformations and convert to binary
  kernel = np.ones((5, 5), np.uint8)
  opening = cv.morphologyEx(gray, cv.MORPH_OPEN, kernel)
  __, binary = cv.threshold(opening, 1, 255, cv.THRESH_TRIANGLE)

  #Finding Contours
  contours, hierarchy = cv.findContours(binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
  contours = sorted(contours, key=cv.contourArea, reverse=True)
  #getting the largest contour
  largest_contour = contours[0]
  cv.drawContours(ref, largest_contour, -1, (255, 255, 255), 7) #drawing the contour on the ref canvas

  #Reparing contoured
  repair = fillByLine(ref, "V")
  repair = fillByLine(repair, "H")
  repair = floodFill(repair)

  mask = repair

  cv.imwrite(maskPath, mask)
  return True

    

