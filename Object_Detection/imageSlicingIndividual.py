from imageSlicingClasses import imageSlicing
import cv2 as cv

#input image
img = cv.imread("./mask.jpg")

img_slicer = imageSlicing(img)
result = img_slicer.imageSlicing()

for i, res in enumerate(result):
    cv.imwrite(f"./Quadrant {i+1}.jpg", res)