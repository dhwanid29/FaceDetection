import streamlit as st
import boto3
import os
import uuid
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize S3 client
s3_client = boto3.client('s3')


def multipart_upload(file_path, bucket_name, folder_name, object_name):
    """Upload a file in parts to an S3 bucket inside a specified folder."""
    try:
        full_object_name = f"{folder_name}/{object_name}"
        response = s3_client.create_multipart_upload(
            Bucket=bucket_name,
            Key=full_object_name,
            ContentType="image/jpeg" if object_name.lower().endswith(".jpg") or object_name.lower().endswith(".jpeg") else "image/png"
        )
        upload_id = response['UploadId']

        parts = []
        chunk_size = 5 * 1024 * 1024  # 5MB
        with open(file_path, 'rb') as file:
            for part_number, chunk in enumerate(iter(lambda: file.read(chunk_size), b''), 1):
                part_response = s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=full_object_name,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk
                )
                parts.append({'ETag': part_response['ETag'], 'PartNumber': part_number})

        s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=full_object_name,
            MultipartUpload={'Parts': parts},
            UploadId=upload_id
        )

        return full_object_name  # Return object path

    except Exception as e:
        print(f"Error uploading {object_name}: {e}")
        if 'upload_id' in locals():
            s3_client.abort_multipart_upload(Bucket=bucket_name, Key=full_object_name, UploadId=upload_id)
        return None



def generate_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a pre-signed URL for an S3 object."""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"Error generating pre-signed URL: {e}")
        return None


def create_preview_html(image_links, bucket_name, folder_name):
    """Create an HTML file with image previews, view, and download buttons."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Gallery</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; }
        h2 { color: #333; }
        .gallery { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .image-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 10px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2);
            background: #fff;
        }
        .gallery img { width: 200px; height: auto; border-radius: 10px; cursor: pointer; }
        .btn-group { margin-top: 10px; display: flex; gap: 10px; }
        .btn {
            padding: 8px 15px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .view-btn { background: #007bff; color: white; text-decoration: none; }
        .download-btn { background: #28a745; color: white; text-decoration: none; }
        .btn:hover { opacity: 0.8; }
    </style>
</head>
<body>
    <h2>Uploaded Images</h2>
    <div class="gallery">
"""

    for link in image_links:
        html_content += f"""
        <div class="image-container">
            <a href="{link}" target="_blank">
                <img src="{link}" alt="Uploaded Image">
            </a>
            <div class="btn-group">
                <a href="{link}" target="_blank" class="btn view-btn">🔍 View</a>
                <a href="{link}" download class="btn download-btn">⬇ Download</a>
            </div>
        </div>
        """

    html_content += """
    </div>
</body>
</html>
"""

    # Save HTML file locally
    html_file_name = f"{folder_name}/gallery.html"
    with open("gallery.html", "w") as f:
        f.write(html_content)

    # Upload HTML file to S3
    s3_client.upload_file("gallery.html", bucket_name, html_file_name, ExtraArgs={'ContentType': 'text/html'})

    # Remove local file
    os.remove("gallery.html")

    return html_file_name  # Return HTML file path in S3


def upload_multiple_images_to_s3(files, bucket_name):
    """Upload multiple images, create an HTML preview file, and return the preview page link."""
    session_id = str(uuid.uuid4())  # Unique folder for this upload session
    folder_name = f"uploads/{session_id}"
    image_links = []

    for file in files:
        object_name = file.name
        with open(file.name, "wb") as f:
            f.write(file.read())

        object_path = multipart_upload(file.name, bucket_name, folder_name, object_name)
        if object_path:
            presigned_url = generate_presigned_url(bucket_name, object_path)
            if presigned_url:
                image_links.append(presigned_url)

        os.remove(file.name)

    # Create and upload preview HTML file
    html_object_path = create_preview_html(image_links, bucket_name, folder_name)

    # Generate pre-signed URL for the HTML file
    return generate_presigned_url(bucket_name, html_object_path)


# Streamlit App
st.title("S3 Bulk Image Uploader with Preview & Download")

bucket_name = st.text_input("Enter S3 Bucket Name", "poc-drive-for-photographers")
uploaded_files = st.file_uploader("Upload Images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if st.button("Upload"):
    if not bucket_name.strip():
        st.error("Please enter a valid bucket name.")
    elif uploaded_files:
        with st.spinner("Uploading..."):
            gallery_link = upload_multiple_images_to_s3(uploaded_files, bucket_name)

        if gallery_link:
            st.success("Files uploaded successfully!")
            st.write("### View Uploaded Images:")
            st.markdown(f"[Click to View Image Gallery]({gallery_link})")
        else:
            st.error("Failed to generate a preview link.")
    else:
        st.warning("Please upload at least one file.")

# import streamlit as st
# import boto3
# import os
# import uuid
# from botocore.exceptions import ClientError
# from dotenv import load_dotenv
#
# # Load environment variables
# load_dotenv()
#
# # Initialize S3 client
# s3_client = boto3.client('s3')
#
#
# def multipart_upload(file_path, bucket_name, folder_name, object_name):
#     """Upload a file in parts to an S3 bucket inside a specified folder."""
#     try:
#         full_object_name = f"{folder_name}/{object_name}"
#         response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=full_object_name)
#         upload_id = response['UploadId']
#
#         parts = []
#         chunk_size = 5 * 1024 * 1024  # 5MB
#         with open(file_path, 'rb') as file:
#             for part_number, chunk in enumerate(iter(lambda: file.read(chunk_size), b''), 1):
#                 part_response = s3_client.upload_part(
#                     Bucket=bucket_name,
#                     Key=full_object_name,
#                     PartNumber=part_number,
#                     UploadId=upload_id,
#                     Body=chunk
#                 )
#                 parts.append({'ETag': part_response['ETag'], 'PartNumber': part_number})
#
#         s3_client.complete_multipart_upload(
#             Bucket=bucket_name,
#             Key=full_object_name,
#             MultipartUpload={'Parts': parts},
#             UploadId=upload_id
#         )
#         return full_object_name  # Return object path
#
#     except Exception as e:
#         print(f"Error uploading {object_name}: {e}")
#         if 'upload_id' in locals():
#             s3_client.abort_multipart_upload(Bucket=bucket_name, Key=full_object_name, UploadId=upload_id)
#         return None
#
#
# def generate_presigned_url(bucket_name, object_name, expiration=3600):
#     """Generate a pre-signed URL for an S3 object."""
#     try:
#         url = s3_client.generate_presigned_url(
#             'get_object',
#             Params={'Bucket': bucket_name, 'Key': object_name},
#             ExpiresIn=expiration
#         )
#         return url
#     except ClientError as e:
#         print(f"Error generating pre-signed URL: {e}")
#         return None
#
#
# def create_preview_html(image_links, bucket_name, folder_name):
#     """Create an HTML file with image previews and upload it to S3."""
#     html_content = """<!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Image Gallery</title>
#     <style>
#         body { font-family: Arial, sans-serif; text-align: center; }
#         h2 { color: #333; }
#         .gallery { display: flex; flex-wrap: wrap; justify-content: center; }
#         .gallery img { margin: 10px; width: 200px; height: auto; border-radius: 10px; box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2); }
#     </style>
# </head>
# <body>
#     <h2>Uploaded Images</h2>
#     <div class="gallery">
# """
#
#     for link in image_links:
#         html_content += f'<img src="{link}" alt="Uploaded Image">'
#
#     html_content += """
#     </div>
# </body>
# </html>
# """
#
#     # Save HTML file locally
#     html_file_name = f"{folder_name}/gallery.html"
#     with open("gallery.html", "w") as f:
#         f.write(html_content)
#
#     # Upload HTML file to S3
#     s3_client.upload_file("gallery.html", bucket_name, html_file_name, ExtraArgs={'ContentType': 'text/html'})
#
#     # Remove local file
#     os.remove("gallery.html")
#
#     return html_file_name  # Return HTML file path in S3
#
#
# def upload_multiple_images_to_s3(files, bucket_name):
#     """Upload multiple images, create an HTML preview file, and return the preview page link."""
#     session_id = str(uuid.uuid4())  # Unique folder for this upload session
#     folder_name = f"uploads/{session_id}"
#     image_links = []
#
#     for file in files:
#         object_name = file.name
#         with open(file.name, "wb") as f:
#             f.write(file.read())
#
#         object_path = multipart_upload(file.name, bucket_name, folder_name, object_name)
#         if object_path:
#             presigned_url = generate_presigned_url(bucket_name, object_path)
#             if presigned_url:
#                 image_links.append(presigned_url)
#
#         os.remove(file.name)
#
#     # Create and upload preview HTML file
#     html_object_path = create_preview_html(image_links, bucket_name, folder_name)
#
#     # Generate pre-signed URL for the HTML file
#     return generate_presigned_url(bucket_name, html_object_path)
#
#
# # Streamlit App
# st.title("S3 Bulk Image Uploader with Preview")
#
# bucket_name = st.text_input("Enter S3 Bucket Name", "poc-drive-for-photographers")
# uploaded_files = st.file_uploader("Upload Images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
#
# if st.button("Upload"):
#     if not bucket_name.strip():
#         st.error("Please enter a valid bucket name.")
#     elif uploaded_files:
#         with st.spinner("Uploading..."):
#             gallery_link = upload_multiple_images_to_s3(uploaded_files, bucket_name)
#
#         if gallery_link:
#             st.success("Files uploaded successfully!")
#             st.write("### View Uploaded Images:")
#             st.markdown(f"[Click to View Image Gallery]({gallery_link})")
#         else:
#             st.error("Failed to generate a preview link.")
#     else:
#         st.warning("Please upload at least one file.")

# import streamlit as st
# import boto3
# import os
# from botocore.exceptions import NoCredentialsError, ClientError
# from dotenv import load_dotenv
#
# # Load environment variables from .env file
# load_dotenv()
#
# # Initialize S3 client (Environment variables or AWS CLI configuration)
# s3_client = boto3.client('s3')
#
# def multipart_upload(file_path, bucket_name, object_name):
#     try:
#         # Create a multipart upload
#         response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_name)
#         upload_id = response['UploadId']
#         print(f"Created Multipart Upload for {object_name}: {upload_id}")
#
#         # Upload parts
#         parts = []
#         chunk_size = 5 * 1024 * 1024  # 5 MB
#         with open(file_path, 'rb') as file:
#             for part_number, chunk in enumerate(iter(lambda: file.read(chunk_size), b''), 1):
#                 part_response = s3_client.upload_part(
#                     Bucket=bucket_name,
#                     Key=object_name,
#                     PartNumber=part_number,
#                     UploadId=upload_id,
#                     Body=chunk
#                 )
#                 parts.append({'ETag': part_response['ETag'], 'PartNumber': part_number})
#
#         # Complete the upload
#         s3_client.complete_multipart_upload(
#             Bucket=bucket_name,
#             Key=object_name,
#             MultipartUpload={'Parts': parts},
#             UploadId=upload_id
#         )
#         print(f"Multipart upload completed for {object_name}.")
#
#     except Exception as e:
#         print(f"Error uploading {object_name}: {e}")
#         # Abort multipart upload in case of failure
#         if 'upload_id' in locals():
#             s3_client.abort_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id)
#
# def upload_multiple_images_to_s3(files, bucket_name):
#     for file in files:
#         object_name = file.name
#         # Save file to a temporary location
#         with open(file.name, "wb") as f:
#             f.write(file.read())
#         # Upload to S3
#         multipart_upload(file.name, bucket_name, object_name)
#         # Clean up local temporary file
#         os.remove(file.name)
#
# # Streamlit App
# st.title("S3 Image Uploader")
#
# # Bucket name input
# bucket_name = st.text_input("Enter S3 Bucket Name", "poc-drive-for-photographers")
#
# # File uploader
# uploaded_files = st.file_uploader("Upload Images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
#
# # Upload button
# if st.button("Upload"):
#     if not bucket_name.strip():
#         st.error("Please enter a valid bucket name.")
#     elif uploaded_files:
#         with st.spinner("Uploading..."):
#             upload_multiple_images_to_s3(uploaded_files, bucket_name)
#         st.success("All files uploaded successfully!")
#     else:
#         st.warning("Please upload at least one file.")




# import boto3
# from botocore.exceptions import NoCredentialsError, ClientError
# from dotenv import load_dotenv
# import os
#
# # Load environment variables from .env file
# load_dotenv()
#
# # Initialize S3 client (Option 1: From environment variables or AWS CLI configuration)
# s3_client = boto3.client('s3')
#
# def multipart_upload(file_path, bucket_name, object_name):
#     try:
#         # Create a multipart upload
#         response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_name)
#         upload_id = response['UploadId']
#         print(f"Created Multipart Upload for {object_name}: {upload_id}")
#
#         # Upload parts
#         parts = []
#         chunk_size = 5 * 1024 * 1024  # 5 MB
#         with open(file_path, 'rb') as file:
#             for part_number, chunk in enumerate(iter(lambda: file.read(chunk_size), b''), 1):
#                 part_response = s3_client.upload_part(
#                     Bucket=bucket_name,
#                     Key=object_name,
#                     PartNumber=part_number,
#                     UploadId=upload_id,
#                     Body=chunk
#                 )
#                 parts.append({'ETag': part_response['ETag'], 'PartNumber': part_number})
#
#         # Complete the upload
#         s3_client.complete_multipart_upload(
#             Bucket=bucket_name,
#             Key=object_name,
#             MultipartUpload={'Parts': parts},
#             UploadId=upload_id
#         )
#         print(f"Multipart upload completed for {object_name}.")
#
#     except Exception as e:
#         print(f"Error uploading {object_name}: {e}")
#         # Abort multipart upload in case of failure
#         if 'upload_id' in locals():
#             s3_client.abort_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id)
#
# def upload_multiple_images(file_paths, bucket_name):
#     """
#     Upload multiple files to S3 using the multipart upload method.
#     :param file_paths: List of file paths to upload.
#     :param bucket_name: Name of the S3 bucket.
#     """
#     for file_path in file_paths:
#         if os.path.isfile(file_path):
#             object_name = os.path.basename(file_path)  # Use the file name as the object name in S3
#             multipart_upload(file_path, bucket_name, object_name)
#         else:
#             print(f"File not found: {file_path}")
#
# # Example Usage: Specify a list of file paths to upload
# file_paths = [
#     "Captured Face_screenshot_27.01.2025.png",
#     "Screenshot from 2025-01-28 11-44-00.png",
#     "Screenshot from 2025-01-28 12-35-05.png"
# ]
# bucket_name = "poc-drive-for-photographers"
#
# upload_multiple_images(file_paths, bucket_name)




# import boto3
# from botocore.exceptions import NoCredentialsError, ClientError
# from dotenv import load_dotenv
#
# load_dotenv()
#
# import boto3
# import os
#
# # Option 1: Load from environment variables or AWS CLI configuration
# s3_client = boto3.client('s3')
#
# # Option 2: Pass credentials directly (not recommended)
# # s3_client = boto3.client(
# #     's3',
# #     aws_access_key_id='your_access_key',
# #     aws_secret_access_key='your_secret_key',
# #     region_name='your_region'
# # )
#
# def multipart_upload(file_path, bucket_name, object_name):
#     try:
#         # Create a multipart upload
#         response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_name)
#         upload_id = response['UploadId']
#         print(f"Created Multipart Upload: {upload_id}")
#
#         # Upload parts
#         parts = []
#         chunk_size = 5 * 1024 * 1024  # 5 MB
#         with open(file_path, 'rb') as file:
#             for part_number, chunk in enumerate(iter(lambda: file.read(chunk_size), b''), 1):
#                 part_response = s3_client.upload_part(
#                     Bucket=bucket_name,
#                     Key=object_name,
#                     PartNumber=part_number,
#                     UploadId=upload_id,
#                     Body=chunk
#                 )
#                 parts.append({'ETag': part_response['ETag'], 'PartNumber': part_number})
#
#         # Complete the upload
#         s3_client.complete_multipart_upload(
#             Bucket=bucket_name,
#             Key=object_name,
#             MultipartUpload={'Parts': parts},
#             UploadId=upload_id
#         )
#         print(f"Multipart upload completed for {object_name}.")
#
#     except Exception as e:
#         print(f"Error: {e}")
#         # Abort multipart upload in case of failure
#         s3_client.abort_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id)
#
# # Example Usage
# file_path = "Captured Face_screenshot_27.01.2025.png"
# bucket_name = "poc-drive-for-photographers"
# object_name = "Captured Face_screenshot_27.01.2025.png"
# multipart_upload(file_path, bucket_name, object_name)

















# def multipart_upload(file_path, bucket_name, object_name):
#     """
#     Upload a file using AWS S3 Multipart Upload.
#     :param file_path: Path to the local file
#     :param bucket_name: Target S3 bucket name
#     :param object_name: Key for the object in S3
#     """
#     s3_client = boto3.client('s3')
#
#     # Start a multipart upload
#     response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_name)
#     upload_id = response['UploadId']
#
#     try:
#         # Read and upload parts in chunks
#         parts = []
#         chunk_size = 5 * 1024 * 1024  # 5 MB
#         with open(file_path, 'rb') as file:
#             part_number = 1
#             while chunk := file.read(chunk_size):
#                 # Upload each part
#                 part_response = s3_client.upload_part(
#                     Bucket=bucket_name,
#                     Key=object_name,
#                     PartNumber=part_number,
#                     UploadId=upload_id,
#                     Body=chunk
#                 )
#                 parts.append({"PartNumber": part_number, "ETag": part_response["ETag"]})
#                 part_number += 1
#
#         # Complete the multipart upload
#         s3_client.complete_multipart_upload(
#             Bucket=bucket_name,
#             Key=object_name,
#             UploadId=upload_id,
#             MultipartUpload={"Parts": parts}
#         )
#         print(f"File '{file_path}' uploaded successfully as '{object_name}'!")
#
#     except Exception as e:
#         # Abort the multipart upload on failure
#         s3_client.abort_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id)
#         print(f"Upload failed: {e}")
#
#
# def upload_multiple_files(file_paths, bucket_name):
#     """
#     Upload multiple files using multipart upload.
#     :param file_paths: List of file paths to upload
#     :param bucket_name: Target S3 bucket name
#     """
#     for file_path in file_paths:
#         object_name = file_path.split('/')[-1]  # Extract file name
#         print(f"Uploading {file_path}...")
#         multipart_upload(file_path, bucket_name, object_name)
#
#
# # Example usage
# if __name__ == "__main__":
#     # Replace with your AWS credentials and bucket name
#     bucket_name = "poc-drive-for-photographers"
#     file_paths = ["file1.txt", "file2.txt", "file3.txt"]  # Replace with actual file paths
#
#     try:
#         upload_multiple_files(file_paths, bucket_name)
#     except NoCredentialsError:
#         print("AWS credentials not found.")
#     except ClientError as e:
#         print(f"An error occurred: {e}")
