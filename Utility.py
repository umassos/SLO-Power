import boto3
from botocore.exceptions import ClientError
import os

class Utility():       
    def convert_from_microwatt_to_watt(self, power_value):
        # return float("{:.2f}".format(power_value / 1000000))
        return round(power_value / 1000000, 2)
    
    def convert_from_watt_to_microwatt(self, power_value):
        return power_value * 1000000

    def convert_from_millisecond_to_second(self, time_value):
        # return float("{:.2f}".format(time_value / 1000))
        return round(time_value / 1000, 2)

    def convert_from_second_to_millisecond(self, time_value):
        return time_value * 1000

    def download_file(self, file_path, bucket, object_name=None):
        '''Download a file from an S3 bucket

        :param file_path: File path to download to
        :param bucket: Bucket to download from
        :param object_name: S3 object name. If not specified then file_path is used
        :return: True if file was downloaded, else False
        '''

        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = os.path.basename(file_path)

        s3 = boto3.client('s3')

        try:
            response = s3.download_file(bucket, object_name, file_path)
        except ClientError as e:
            return False

        return True

    def upload_file(self, file_name, bucket, object_name=None):
        '''Upload a file to an S3 bucket

        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param object_name: S3 object name. If not specified then file_name is used
        :return: True if file was uploaded, else False
        '''

        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = os.path.basename(file_name)

        # Upload the file
        s3_client = boto3.client('s3')
        try:
            response = s3_client.upload_file(file_name, bucket, object_name)
        except ClientError as e:
            return False
        
        return True