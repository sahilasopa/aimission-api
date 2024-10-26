import json
import secrets
from datetime import datetime

import OTPLessAuthSDK
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.conf.global_settings import MEDIA_URL
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from google.auth import compute_engine
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CarboUser, StationProfile, Journey

import requests
import subprocess
import json

from authentication.serializers import StationProfileSerializer, JourneySerializer

otpless_client_id = ""
otpless_client_secret = ""

# read previous trips via id
# cru wishlist, (Create: product id), Update(add balance,  add item)
# wishlist 3rd model
# get user
# transaction from user to user, amount date time, create read


bedrock_client = boto3.client(
    'bedrock-runtime',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)


@csrf_exempt
def call_bedrock(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('input')
            model_id = "meta.llama3-70b-instruct-v1:0"

            formatted_prompt = f"""
            Context:
            You are an AI assistant helping with a specific task. Here’s what you need to know:
            You are to act as a helpful digital assistant for a user on our app. Your role is to help users make sustainable decisions about their transport choices. You have been given the following data set to answer user questions:
            User gains carbon credits for choosing to use public transport over using a cab or a private vehicle
            the carbon credit can be then exchanged for items at marketplace
            CO2 emissions for the drive is to be calculated by you.

            The user will tell you where they want to go and you will evaluate the options of car and mumbai local for them, focusing on sustainability and explaining to them the advantage of taking the public transport. Limit your responses to make them short. Hhighlight the recommended choice clearly at the top and then give a short explanation.
            remember to collect info about mumbai local stations and all mumbai metro routes
            
            if user wants to go from a to b, and the distance from a to closest station to a + train + distance from closest station to b ofsets carbon emitted by car then suggest a car
            
            your end goal is to tell user most efficient path and tell them how much carbon they can save, try to give more than 1 paths

            <|begin_of_text|><|start_header_id|>user<|end_header_id|>
            {user_input}
            <|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            """

            native_request = {
                "prompt": formatted_prompt,
                "max_gen_len": 512,
                "temperature": 0.5,
            }

            request = json.dumps(native_request)

            try:
                response = bedrock_client.invoke_model(modelId=model_id, body=request)
            except (ClientError, Exception) as e:
                print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
                exit(1)

            model_response = json.loads(response["body"].read())

            response_text = str(model_response["generation"]).strip()
            return JsonResponse({'output': response_text})

        except Exception as e:
            print(e)
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


class AddTripsAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        id = data.get("user_id")
        trips = Journey.objects.filter(user_id=id, in_progress=False)
        data = JourneySerializer(trips, many=True).data
        return Response({"data": data})


class ProfileAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        user_id = data.get("id")
        name = data.get("name")
        dob = data.get("dob")
        user = CarboUser.objects.get(pk=user_id)
        user.name = name
        user.dob = dob
        user.save()
        return Response("OK")


class StartJourneyAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        user_id = data.get("user_id")
        type = data.get("type")
        start_station_id = data.get("start_station_id")
        journey = Journey.objects.create(
            user_id=user_id,
            type=type,
            start_stop=StationProfile.objects.get(id=start_station_id),
            in_progress=True,
            start_time=datetime.now(),
        )
        return Response({"id": journey.id})


class StationProfileAPIView(APIView):
    @csrf_exempt
    def get(self, request, *args, **kwargs):
        stations = StationProfile.objects.all()
        serializer = StationProfileSerializer(stations, many=True)
        return Response({"data": serializer.data})


class EstimatedDistanceAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        start_station = StationProfile.objects.get(id=data.get("start_id"))
        end_station = StationProfile.objects.get(id=data.get("end_id"))
        temp = Journey.objects.create(
            user=None,
            type="Train",
            start_stop=start_station,
            end_stop=end_station,
            start_time=datetime.now()
        )
        credits = temp.get_credits()
        temp.delete()
        return Response({"data": credits})


class EndJourneyAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        journey_id = data.get("trip_id")
        end_station_id = data.get("station_id")
        journey = Journey.objects.get(
            id=journey_id
        )
        journey.end_stop = StationProfile.objects.get(id=end_station_id)
        journey.in_progress = False
        journey.end_time = datetime.now()
        journey.save()
        return Response({"credits": journey.get_credits(),
                         "carbon_saved": journey.calculate_carbon_emissions_saved(),
                         "time_taken": journey.calculate_time_taken(),
                         "start_name": journey.start_stop.name,
                         "end_name": journey.end_stop.name
                         })


class SendOtpAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        phone_number = data.get("phoneNumber")
        try:
            otp_details = OTPLessAuthSDK.OTP.send_otp(
                phone_number,
                None,
                "SMS",
                None,
                None,
                "300",
                4,
                otpless_client_id,
                otpless_client_secret
            )
            return Response(otp_details, status=200)
        except Exception as e:
            print(f"An error occurred: {e}")
            return Response({"message": "Error Occurred"}, status=400)


class VerifyOtpAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        phone_number = data.get("phoneNumber")
        try:
            otp_details = OTPLessAuthSDK.OTP.veriy_otp(
                data.get("orderId"),
                data.get("otp"),
                None,
                phone_number,
                otpless_client_id,
                otpless_client_secret
            )
            if otp_details.get('isOTPVerified'):
                uid = ''.join(
                    secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(28)
                )
                user = CarboUser.objects.filter(phone_number=phone_number).first()
                if user is not None:
                    return Response({"uid": user.id}, status=200)
                else:
                    CarboUser.objects.create(
                        id=uid,
                        name=data.get("name"),
                        phone_number=phone_number,
                    )
                return Response({
                    "isVerified": True,
                    "uid": uid,
                }, status=200)
            else:
                return Response({
                    "isVerified": False,
                    "message": "Invalid OTP"
                }, status=401)
        except Exception as e:
            print(f"An error occurred: {e}")
            return Response({"message": "Error Occurred"}, status=400)


class ResendOtpAPIView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        try:
            OTPLessAuthSDK.OTP.resend_otp(
                data.get("order_id"),
                otpless_client_id,
                otpless_client_secret
            )
            return Response(status=200)
        except Exception as e:
            print(f"An error occurred: {e}")
            return Response({"message": "Please try later"}, status=400)


from google.auth.transport.requests import Request


def analyze_image(image_url):
    credentials = compute_engine.Credentials()
    request = Request()
    access_token = credentials.refresh(request).token
    endpoint = "us-central1-aiplatform.googleapis.com"
    region = "us-central1"
    project_id = "aimission-mumbaihacks"
    url = f"https://{endpoint}/v1beta1/projects/{project_id}/locations/{region}/endpoints/openapi/chat/completions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama-3.2-90b-vision-instruct-maas",
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"image_url": {"url": image_url}, "type": "image_url"},
                    {"text": "What’s in this image?", "type": "text"}
                ]
            }
        ],
        "max_tokens": 40,
        "temperature": 0.4,
        "top_k": 10,
        "top_p": 0.95,
        "n": 1
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print("RESPONSE IS")
    print(response)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


#
# # Example usage:
# image_url = "gs://github-repo/img/gemini/intro/landmark3.jpg"
# try:
#     result = analyze_image(image_url)
#     print("Response:", result)
# except Exception as e:
#     print(e)


class TicketScanAPIView(APIView):
    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        try:
            user_id = request.POST.get("id", None)
            ticket_image = request.FILES.get("ticket_image", None)

            if not ticket_image:
                return Response({"error": "No ticket image provided"}, status=status.HTTP_400_BAD_REQUEST)

            # Save the uploaded file
            file_path = default_storage.save(f'tickets/{ticket_image.name}', ticket_image)

            # Construct GCS path
            gcs_bucket_name = "mumbaihacks-aimmision"  # Ensure you set this in your settings
            gcs_file_path = f"gs://{gcs_bucket_name}/{file_path}"

            # Process the image
            analysis_result = analyze_image(gcs_file_path)  # Pass the GCS path to analyze_image

            return Response({"analysis": analysis_result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# few shot prompting
