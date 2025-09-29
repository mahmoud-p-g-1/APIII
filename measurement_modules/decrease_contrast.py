from __future__ import print_function
import cv2 as cv
import numpy as np
import argparse
from photos_height import *

# Read image given by user


image = cv.imread(front_input_image)
new_image = np.zeros(image.shape, image.dtype)

image_side = cv.imread(side_input_image)
new_image_side = np.zeros(image_side.shape, image_side.dtype)

alpha = 1.0  #contrast
beta = 0 #brightness

try:
    alpha = float(1)
    beta = int(50)
except ValueError:
    print('Error, not a number')


for y in range(image.shape[0]):
    for x in range(image.shape[1]):
        for c in range(image.shape[2]):
            new_image[y, x, c] = np.clip(alpha * image[y, x, c] + beta, 0, 255)

cv.imwrite('images/degrease_contrast.jpg', new_image)
print("degrease contrast and saved on degrease_contrast.jpg")

for y in range(image_side.shape[0]):
    for x in range(image_side.shape[1]):
        for c in range(image_side.shape[2]):
            new_image_side[y, x, c] = np.clip(alpha * image_side[y, x, c] + beta, 0, 255)

cv.imwrite('images/degrease_contrast_side.jpg', new_image_side)
print("degrease contrast and saved on degrease_contrast_side.jpg")