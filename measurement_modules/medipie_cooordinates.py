import cv2
import mediapipe as mp
from photos_height import *

# Initialize MediaPipe pose solution
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

# Drawing utilities to visualize landmarks
mp_drawing = mp.solutions.drawing_utils

landmark_names = {
    0: "Nose", 1: "Left Eye Inner", 2: "Left Eye", 3: "Left Eye Outer", 4: "Right Eye Inner", 5: "Right Eye",
    6: "Right Eye Outer", 7: "Left Ear", 8: "Right Ear", 9: "Mouth Left", 10: "Mouth Right", 11: "Left Shoulder",
    12: "Right Shoulder", 13: "Left Elbow", 14: "Right Elbow", 15: "Left Wrist", 16: "Right Wrist", 17: "Left Pinky",
    18: "Right Pinky", 19: "Left Index", 20: "Right Index", 21: "Left Thumb", 22: "Right Thumb", 23: "Left Hip",
    24: "Right Hip", 25: "Left Knee", 26: "Right Knee", 27: "Left Ankle", 28: "Right Ankle", 29: "Left Heel",
    30: "Right Heel", 31: "Left Foot Index", 32: "Right Foot Index"
}
landmark_names_side = {
    0: "Nose side", 1: "Left Eye Inner side", 2: "Left Eye side", 3: "Left Eye Outer side", 4: "Right Eye Inner side", 5: "Right Eye side",
    6: "Right Eye Outer side", 7: "Left Ear side", 8: "Right Ear side", 9: "Mouth Left side", 10: "Mouth Right side", 11: "Left Shoulder side",
    12: "Right Shoulder side", 13: "Left Elbow side", 14: "Right Elbow side", 15: "Left Wrist side", 16: "Right Wrist side", 17: "Left Pinky side",
    18: "Right Pinky side", 19: "Left Index side", 20: "Right Index side", 21: "Left Thumb side", 22: "Right Thumb side", 23: "Left Hip side",
    24: "Right Hip side", 25: "Left Knee side", 26: "Right Knee side", 27: "Left Ankle side", 28: "Right Ankle side", 29: "Left Heel side",
    30: "Right Heel side", 31: "Left Foot Index side", 32: "Right Foot Index side"
}

image_front = cv2.imread(front_input_image)
image_side = cv2.imread(side_input_image)

image_rgb_front = cv2.cvtColor(image_front, cv2.COLOR_BGR2RGB)
image_rgb_side = cv2.cvtColor(image_side, cv2.COLOR_BGR2RGB)

result_front = pose.process(image_rgb_front)
result_side = pose.process(image_rgb_side)

if result_front.pose_landmarks:
    mp_drawing.draw_landmarks(image_front, result_front.pose_landmarks, mp_pose.POSE_CONNECTIONS)
    height, width, _ = image_front.shape

    # Print landmark coordinates with body part names
    for id, landmark in enumerate(result_front.pose_landmarks.landmark):
        x = int(landmark.x * width)
        y = int(landmark.y * height)

        # Get the corresponding body part name from the dictionary
        body_part = landmark_names.get(id, "Unknown")

        # Print the body part name and coordinates
        print(f'{body_part}: (X: {x}, Y: {y})')

        #Display the image with pose landmarks
    #cv2.imshow('Pose Detection', image_front)
    #cv2.waitKey(0)  # Wait for a key press to close the window
    #cv2.destroyAllWindows()
    cv2.imwrite('images/medipipe_output.jpg', image_front)
else:
    pass

if result_front.pose_landmarks:
    # Get image dimensions
    height, width, _ = image_front.shape


    # Convert normalized coordinates to pixel coordinates for each landmark
    def get_coords(landmark):
        return int(landmark.x * width), int(landmark.y * height)

    landmarks = result_front.pose_landmarks.landmark
    nose = get_coords(landmarks[0])
    left_eye_inner = get_coords(landmarks[1])
    left_eye = get_coords(landmarks[2])
    left_eye_outer = get_coords(landmarks[3])
    right_eye_inner = get_coords(landmarks[4])
    right_eye = get_coords(landmarks[5])
    right_eye_outer = get_coords(landmarks[6])
    left_ear = get_coords(landmarks[7])
    right_ear = get_coords(landmarks[8])
    mouth_left = get_coords(landmarks[9])
    mouth_right = get_coords(landmarks[10])
    left_shoulder = get_coords(landmarks[11])
    right_shoulder = get_coords(landmarks[12])
    left_elbow = get_coords(landmarks[13])
    right_elbow = get_coords(landmarks[14])
    left_wrist = get_coords(landmarks[15])
    right_wrist = get_coords(landmarks[16])
    left_pinky = get_coords(landmarks[17])
    right_pinky = get_coords(landmarks[18])
    left_index = get_coords(landmarks[19])
    right_index = get_coords(landmarks[20])
    left_thumb = get_coords(landmarks[21])
    right_thumb = get_coords(landmarks[22])
    left_hip = get_coords(landmarks[23])
    right_hip = get_coords(landmarks[24])
    left_knee = get_coords(landmarks[25])
    right_knee = get_coords(landmarks[26])
    left_ankle = get_coords(landmarks[27])
    right_ankle = get_coords(landmarks[28])
    left_heel = get_coords(landmarks[29])
    right_heel = get_coords(landmarks[30])
    left_foot_index = get_coords(landmarks[31])
    right_foot_index = get_coords(landmarks[32])

if result_side.pose_landmarks:
    mp_drawing.draw_landmarks(image_side, result_side.pose_landmarks, mp_pose.POSE_CONNECTIONS)
    height_side, width_side, _ = image_side.shape

    # Print landmark coordinates with body part names
    for id, landmark in enumerate(result_side.pose_landmarks.landmark):
        x_side = int(landmark.x * width_side)
        y_side = int(landmark.y * height_side)

        # Get the corresponding body part name from the dictionary
        body_part_side = landmark_names_side.get(id, "Unknown")

        # Print the body part name and coordinates
        print(f'{body_part_side}: (X_side: {x_side}, Y_side: {y_side})')

        #Display the image with pose landmarks
    #cv2.imshow('Pose Detection', image_front)
    #cv2.waitKey(0)  # Wait for a key press to close the window
    #cv2.destroyAllWindows()
    cv2.imwrite('images/medipipe_output_side.jpg', image_side)
else:
    pass

if result_side.pose_landmarks:
    # Get image dimensions
    height_side, width_side, _ = image_side.shape


    # Convert normalized coordinates to pixel coordinates for each landmark
    def get_coords(landmark):
        return int(landmark.x * width_side), int(landmark.y * height_side)


    # Extract each joint by name
    landmarks_side = result_side.pose_landmarks.landmark
    nose_side = get_coords(landmarks_side[0])
    left_eye_inner_side = get_coords(landmarks_side[1])
    left_eye_side = get_coords(landmarks_side[2])
    left_eye_outer_side = get_coords(landmarks_side[3])
    right_eye_inner_side = get_coords(landmarks_side[4])
    right_eye_side = get_coords(landmarks_side[5])
    right_eye_outer_side = get_coords(landmarks_side[6])
    left_ear_side = get_coords(landmarks_side[7])
    right_ear_side = get_coords(landmarks_side[8])
    mouth_left_side = get_coords(landmarks_side[9])
    mouth_right_side = get_coords(landmarks_side[10])
    left_shoulder_side = get_coords(landmarks_side[11])
    right_shoulder_side = get_coords(landmarks_side[12])
    left_elbow_side = get_coords(landmarks_side[13])
    right_elbow_side = get_coords(landmarks_side[14])
    left_wrist_side = get_coords(landmarks_side[15])
    right_wrist_side = get_coords(landmarks_side[16])
    left_pinky_side = get_coords(landmarks_side[17])
    right_pinky_side = get_coords(landmarks_side[18])
    left_index_side = get_coords(landmarks_side[19])
    right_index_side = get_coords(landmarks_side[20])
    left_thumb_side = get_coords(landmarks_side[21])
    right_thumb_side = get_coords(landmarks_side[22])
    left_hip_side = get_coords(landmarks_side[23])
    right_hip_side = get_coords(landmarks_side[24])
    left_knee_side = get_coords(landmarks_side[25])
    right_knee_side = get_coords(landmarks_side[26])
    left_ankle_side = get_coords(landmarks_side[27])
    right_ankle_side = get_coords(landmarks_side[28])
    left_heel_side = get_coords(landmarks_side[29])
    right_heel_side = get_coords(landmarks_side[30])
    left_foot_index_side = get_coords(landmarks_side[31])
    right_foot_index_side = get_coords(landmarks_side[32])

