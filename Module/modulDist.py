import math
import cv2


def calculate_focal_length(known_distance, known_width, pixel_width):
    # "\""
    # Melakukan kalibrasi nilai focal length kamera.
    
    # Parameters:
    # - known_distance (float): Jarak objek sebenarnya ke kamera (misal dalam cm).
    # - known_width (float): Lebar objek sebenarnya (misal ICD wajah asli dalam cm).
    # - pixel_width (float): Lebar objek dalam satuan pixel pada gambar kamera.
    
    # Returns:
    # - float: Nilai focal length.
    # "\""
    if pixel_width <= 0:
        return 0
    focal_length = (pixel_width * known_distance) / known_width
    return focal_length

def distance_to_camera(focal_length, known_width, pixel_width):
    # "\""
    # Mendeteksi dan menghitung jarak objek ke kamera berdasarkan focal length.
    
    # Parameters:
    # - focal_length (float): Nilai focal length hasil kalibrasi.
    # - known_width (float): Lebar objek sebenarnya (misal ICD wajah asli dalam cm).
    # - pixel_width (float): Lebar objek dalam satuan pixel pada gambar kamera saat ini.
    
    # Returns:
    # - float: Jarak objek dari kamera pada saat ini (cm).
    # "\""
    if pixel_width <= 0:
        return 0
        
    distance = (known_width * focal_length) / pixel_width
    return distance
