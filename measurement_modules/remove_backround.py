
from rembg import remove
import cv2

input_path = 'images/degrease_contrast.jpg'
output_path = 'images/remove.jpg'

input_main = cv2.imread(input_path)
output = remove(input_main)
cv2.imwrite(output_path, output)

print("removed background and saved the image to remove.jpg")

input_path_side = 'images/degrease_contrast_side.jpg'
output_path_side = 'images/remove_side.jpg'

input_main_side = cv2.imread(input_path_side)
output_side = remove(input_main_side)
cv2.imwrite(output_path_side, output_side)

print("removed background and saved the image to remove_side.jpg")
