import numpy as np
import cv2 as cv
import glob

criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

pattern_size = (7, 5)  # columns, rows
objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
# Arrays to store object points and image points from all the images.
objpoints = []  # 3d point in real world space
imgpoints = []  # 2d points in image plane.

images = glob.glob('attachments (4)/*jpg')

for fname in images:
    img = cv.imread(fname)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    # Find the chess board corners
    ret, corners = cv.findChessboardCorners(gray, (7, 5), None)
    # If found, add object points, image points (after refining them)
    if ret:
        objpoints.append(objp)
        corners2 = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

        # Draw and display the corners
        cv.drawChessboardCorners(img, (7, 5), corners2, ret)
        # cv.imshow('img', img)
        # cv.waitKey()
        cv.imwrite('*.jpg', img)
cv.destroyAllWindows()

image_names = ['test_images/exp1_front.jpg', 'test_images/exp1_side.jpg',
               'test_images/exp2_front.jpg', 'test_images/exp2_side.jpg',
               'test_images/exp3_front.jpg', 'test_images/exp3_side.jpg',
               'test_images/exp4_front.jpg', 'test_images/exp4_side.jpg',
               'test_images/exp5_front.jpg', 'test_images/exp5_side.jpg',
               'test_images/exp6_front.jpg', 'test_images/exp6_side.jpg',
               'test_images/exp7_front.jpg', 'test_images/exp7_side.jpg',
               'test_images/exp8_front.jpg', 'test_images/exp8_side.jpg',
               'test_images/exp9_front.jpg', 'test_images/exp9_side.jpg',
               'test_images/exp10_front.jpg', 'test_images/exp10_side.jpg',
               'test_images/exp11_front.jpg', 'test_images/exp11_side.jpg']
image_outputs = ['test_images_calibrated/exp1_front_cal.jpg', 'test_images_calibrated/exp1_side_cal.jpg',
                 'test_images_calibrated/exp2_front_cal.jpg', 'test_images_calibrated/exp2_side_cal.jpg',
                 'test_images_calibrated/exp3_front_cal.jpg', 'test_images_calibrated/exp3_side_cal.jpg',
                 'test_images_calibrated/exp4_front_cal.jpg', 'test_images_calibrated/exp4_side_cal.jpg',
                 'test_images_calibrated/exp5_front_cal.jpg', 'test_images_calibrated/exp5_side_cal.jpg',
                 'test_images_calibrated/exp6_front_cal.jpg', 'test_images_calibrated/exp6_side_cal.jpg',
                 'test_images_calibrated/exp7_front_cal.jpg', 'test_images_calibrated/exp7_side_cal.jpg',
                 'test_images_calibrated/exp8_front_cal.jpg', 'test_images_calibrated/exp8_side_cal.jpg',
                 'test_images_calibrated/exp9_front_cal.jpg', 'test_images_calibrated/exp9_side_cal.jpg',
                 'test_images_calibrated/exp10_front_cal.jpg', 'test_images_calibrated/exp10_side_cal.jpg',
                 'test_images_calibrated/exp11_front_cal.jpg', 'test_images_calibrated/exp11_side_cal.jpg']


ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

for x in range(22):
    img = cv.imread(image_names[x])
    h, w = img.shape[:2]
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
    # undistort
    dst = cv.undistort(img, mtx, dist, None, newcameramtx)
    # crop the image
    # x, y, w, h = roi
    # dst = dst[y:y+h, x:x+w]
    cv.imwrite(image_outputs[x], dst)
