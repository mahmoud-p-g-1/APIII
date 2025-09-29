from PIL import Image

img = Image.open('images/remove.jpg')
width = img.size[0]
height = img.size[1]
for i in range(0, width):  # process all pixels
    for j in range(0, height):
        data = img.getpixel((i, j))
        if data[0] < 5 and data[1] < 5 and data[2] < 5:
            img.putpixel((i, j), (0, 0, 0))
        else:
            # Put white
            img.putpixel((i, j), (255, 255, 255))



output_filename = "images/add_silhouette.jpg"
try:
    img.save(output_filename)
    print(f"Image successfully saved as '{output_filename}'")
except Exception as e:
    print("An error occurred while saving the image:", e)


img_side = Image.open('images/remove_side.jpg')
width_side = img_side.size[0]
height_side = img_side.size[1]
for i in range(0, width_side):  # process all pixels
    for j in range(0, height_side):
        data_side = img_side.getpixel((i, j))
        if data_side[0] < 5 and data_side[1] < 5 and data_side[2] < 5:
            img_side.putpixel((i, j), (0, 0, 0))
        else:
            # Put white
            img_side.putpixel((i, j), (255, 255, 255))



output_filename_side = "images/add_silhouette_side.jpg"
try:
    img_side.save(output_filename_side)
    print(f"Image successfully saved as '{output_filename_side}'")
except Exception as e:
    print("An error occurred while saving the image:", e)