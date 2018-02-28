# -*- coding: utf-8 -*-
from twilio.rest import Client
import os
import sys
import urllib
import requests
import json
from flask import Flask, request, Response, make_response, jsonify, send_from_directory
# from flask_cors import CORS, cross_origin
from requests.auth import HTTPBasicAuth
import logging
from contextlib import closing
# Twilio Helper Library
from twilio.twiml.voice_response import VoiceResponse, Gather , Sip , Dial
# AWS Python SDK
import boto3
from datetime import datetime
from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import SyncGrant
from twilio.twiml.voice_response import VoiceResponse, Gather


# Setup global variables
apiai_client_access_key = os.environ["APIAPI_CLIENT_ACCESS_KEY"]
aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
aws_secret_key = os.environ["AWS_SECRET_KEY"]
mnsphonenumber = os.environ["MNS_SNS_NUMBER"]
twilio_sync_service_id = os.environ["TWILIO_SYNC_SID"]
twilio_account_sid = os.environ["TWILIO_ACCOUNT_SID"]
twilio_auth_token = os.environ["TWILIO_AUTH_TOKEN"]
twilio_api_key = os.environ["TWILIO_API_KEY"]
twilio_api_secret = os.environ["TWILIO_API_SECRET"]
access_key = os.environ["ACCESS_KEY"]
mns_genesys_sip = os.environ["TWILIO_GENESYS_SIP"]
dialSip = Dial()
dialSip.sip(mns_genesys_sip+'?mycustomheader=foo&myotherheader=bar');


sync_map = 'ASRBotEvents'
syncUrl = 'https://sync.twilio.com/v1/Services/' + twilio_sync_service_id + '/Maps/' + sync_map + '/Items'

apiai_url = "https://api.api.ai/v1/query"
apiai_querystring = {"v": "20150910"}
registered_users = {"+447477471234": "Akash",
                   "+447481191234": "Customer"
}
# Adjust the hints for improved Speech to Text
hints = "1 one first, 2 two second, 20 twenty, 25 twentyfifth, 6 sixth twentysixth, sir albert, westin, hyatt, inter continental, march, april, may, june"

app = Flask(__name__)

@app.route('/start', methods=['GET','POST'])
def start():
    caller_phone_number = request.values.get('From')
    user_id = request.values.get('CallSid')
    polly_voiceid = request.values.get('polly_voiceid', "Joanna")
    twilio_asr_language = request.values.get('twilio_asr_language', "en-US")
    apiai_language = request.values.get('apiai_language', "en")
    caller_name = registered_users.get(caller_phone_number, " ")
    hostname = request.url_root

    # Initialize API.AI Bot
    headers = {
        'authorization': "Bearer " + apiai_client_access_key,
        'content-type': "application/json"
    }
    payload = {'event': {'name':'mns_sns_uc', 'data': {'user_name': caller_name}},
               'lang': apiai_language,
               'sessionId': user_id
    }
    response = requests.request("POST", url=apiai_url, data=json.dumps(payload), headers=headers, params=apiai_querystring)
    print(response.text)
    output = json.loads(response.text)
    output_text = output['result']['fulfillment']['speech']
    output_text = output_text.decode("utf-8")
    resp = VoiceResponse()

    values = {"prior_text": output_text}
    qs = urllib.urlencode(values)
    action_url = "/process_speech?" + qs
    gather = Gather(input="speech", hints=hints, language=twilio_asr_language, speech_timeout="auto", action=action_url, method="POST")


    if  'https://' in output_text:
        audioFiles = output_text.split('|');
        for audioFile in audioFiles :
    		gather.play(audioFile);
    else:
         # Prepare for next set of user Speech
         # TTS the bot response
         values = {"text": output_text,
                   "polly_voiceid": polly_voiceid,
                   "region": "us-east-1"
         }
         qs = urllib.urlencode(values)

    	 gather.play(hostname + 'polly_text2speech?' + qs)


    resp.append(gather)

    # If gather is missing (no speech), redirect to process speech again
    values = {"force_dialog_state": True,
              "forced_dialog_state": 'complete',
              "prior_text": output_text,
              "polly_voiceid": polly_voiceid,
              "twilio_asr_language": twilio_asr_language,
              "apiai_language": apiai_language,
              "SpeechResult": "",
              "Confidence": 0.0
    }
    qs = urllib.urlencode(values)
    action_url = "/process_speech?" + qs
    resp.redirect(action_url)
    print str(resp)
    return str(resp)

#####
##### Process Twilio ASR: Text to Intent analysis
#####
@app.route('/process_speech', methods=['GET', 'POST'])
def process_speech():
    user_id = request.values.get('CallSid')
    polly_voiceid = request.values.get('polly_voiceid', "Joanna")
    twilio_asr_language = request.values.get('twilio_asr_language', "en-US")
    apiai_language = request.values.get('apiai_language', "en")
    prior_text = request.values.get('prior_text', "Prior text missing")
    prior_dialog_state = request.values.get('prior_dialog_state', "ElicitIntent")
    input_text = request.values.get("SpeechResult", "")
    confidence = float(request.values.get("Confidence", 0.0))
    hostname = request.url_root
    print "Twilio Speech to Text: " + input_text + " Confidence: " + str(confidence)
    sys.stdout.flush()

    forceDialogState=request.values.get("force_dialog_state");
    forcedDialogState=request.values.get("forced_dialog_state");

    if input_text == "":
       input_text = "unknown speech" 


    local_request_dict = {}
    local_request_dict = request.form.to_dict(); 


    resp = VoiceResponse()
    if (confidence >= 0.0):
        # Step 1: Call Bot for intent analysis - API.AI Bot
        
        intent_name, output_text, dialog_state ,apiai_intent_name  = apiai_text_to_intent(apiai_client_access_key, input_text, user_id, apiai_language)

        if forceDialogState :
           dialog_state =  forcedDialogState


        # Step 2: Construct TwiML
        if dialog_state in ['in-progress']:
          if  'https://' in output_text:
             audioFiles = output_text.split('|');
             for audioFile in audioFiles :
                    resp.play(audioFile);
             #resp.dial(mnsphonenumber); 
	     resp.dial.sip(mns_genesys_sip+'?mycustomheader=foo&myotherheader=bar');
	     add_to_sync(local_request_dict,apiai_intent_name)
          else:
            values = {"prior_text": output_text, "prior_dialog_state": dialog_state}
            qs2 = urllib.urlencode(values)
            action_url = "/process_speech?" + qs2
            gather = Gather(input="speech", hints=hints, language=twilio_asr_language, timeout="3", action=action_url,method="POST")
            values = {"text": output_text,
                    "polly_voiceid": polly_voiceid,
                    "region": "us-east-1"
            }
            qs1 = urllib.urlencode(values)
            gather.play(hostname + 'polly_text2speech?' + qs1)
            resp.append(gather)

            # If gather is missing (no speech), redirect to process incomplete speech via the Bot
            values = {"prior_text": output_text,
                      "polly_voiceid": polly_voiceid,
                      "twilio_asr_language": twilio_asr_language,
                      "apiai_language": apiai_language,
                      "SpeechResult": "",
                      "Confidence": 0.0}
            qs3 = urllib.urlencode(values)
            action_url = "/process_speech?" + qs3
            resp.redirect(action_url)
        elif dialog_state in ['complete']:
          print("COMPLETED STATE" + output_text);
	  if  'https://' in output_text:
             audioFiles = output_text.split('|');
             for audioFile in audioFiles :
                    resp.play(audioFile);
             #resp.dial(mnsphonenumber);
	     resp.append(dialSip);
	     add_to_sync(local_request_dict,apiai_intent_name)	
          else:
            values = {"text": output_text,
                    "polly_voiceid": polly_voiceid,
                    "region": "us-east-1"
            }
            qs = urllib.urlencode(values)
            resp.play(hostname + 'polly_text2speech?' + qs)
            #resp.dial(mnsphonenumber)
	    resp.dial.sip(mns_genesys_sip+'?mycustomheader=foo&myotherheader=bar');
	    add_to_sync(local_request_dict, apiai_intent_name)		
        elif dialog_state in ['Failed']:
	  if  'https://' in output_text:
             audioFiles = output_text.split('|');
             for audioFile in audioFiles :
                    resp.play(audioFile);
             #resp.dial(mnsphonenumber);
	     resp.dial.sip(mns_genesys_sip+'?mycustomheader=foo&myotherheader=bar');
	     add_to_sync(local_request_dict,apiai_intent_name)	
          else:
            values = {"text": "I am sorry, there was an error.  Please call again!",
                    "polly_voiceid": polly_voiceid,
                    "region": "us-east-1"
            }
            qs = urllib.urlencode(values)
            resp.play(hostname + 'polly_text2speech?' + qs)
            #resp.dial.number(mnsphonenumber);
            resp.dial.sip(mns_genesys_sip+'?mycustomheader=foo&myotherheader=bar');
    else:
        # We didn't get STT of higher confidence, replay the prior conversation
        output_text = prior_text
        dialog_state = prior_dialog_state
        values = {"prior_text": output_text,
                  "polly_voiceid": polly_voiceid,
                  "twilio_asr_language": twilio_asr_language,
                  "apiai_language": apiai_language,
                  "prior_dialog_state": dialog_state}
        qs2 = urllib.urlencode(values)
        action_url = "/process_speech?" + qs2
        gather = Gather(input="speech", hints=hints, language=twilio_asr_language, timeout="3", action=action_url, method="POST")
        values = {"text": output_text,
                  "polly_voiceid": polly_voiceid,
                  "region": "us-east-1"
                  }
        qs1 = urllib.urlencode(values)
        gather.play(hostname + 'polly_text2speech?' + qs1)
        resp.append(gather)

        values = {"prior_text": output_text,
                  "polly_voiceid": polly_voiceid,
                  "twilio_asr_language": twilio_asr_language,
                  "apiai_language": apiai_language,
                  "prior_dialog_state": dialog_state
                  }
        qs2 = urllib.urlencode(values)
        action_url = "/process_speech?" + qs2
        resp.redirect(action_url)
    print str(resp)
    return str(resp)

#####
##### Google Api.ai - Text to Intent
#####
#@app.route('/apiai_text_to_intent', methods=['GET', 'POST'])
def apiai_text_to_intent(apiapi_client_access_key, input_text, user_id, language):
    headers = {
        'authorization': "Bearer " + apiapi_client_access_key,
        'content-type': "application/json"
    }
    payload = {'query': input_text,
               'lang': language,
               'sessionId': user_id
    }
    response = requests.request("POST", url=apiai_url, data=json.dumps(payload), headers=headers, params=apiai_querystring)
    output = json.loads(response.text)
    print json.dumps(output, indent=2)
    try:
        output_text = output['result']['fulfillment']['speech']
    except:
        output_text = ""
    try:
        intent_stage = output['result']['contexts']
    except:
        intent_stage = "unknown"

    if (output['result']['actionIncomplete']):
        dialog_state = 'in-progress'
    else:
        dialog_state = 'complete'
	
    output_intent_name = output['result']['metadata']['intentName']
    print("Intent Name" + output_intent_name)

    return intent_stage, output_text, dialog_state,output_intent_name

#####
##### API.API fulfillment webhook (You can enable this in API.AI console)
#####
@app.route('/apiai_fulfillment', methods=['GET', 'POST'])
def apiai_fulfillment():
    res = {"speech": "Your booking is confirmed. Have a great day!",
        "displayText": "Your booking is confirmed. Have a great day!",
        "source": "apiai-bookhotel-webhook"
    }
    res = json.dumps(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    print str(r)
    return r


def add_to_sync(request_dict,apiIntent):
    request_dict['initial_question'] = ''
    request_dict['CallDate'] = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    request_dict['Intent'] = apiIntent
    callback_data = json.dumps(request_dict)
    # print(callback_data)

    item_key = request_dict['CallSid']
    new_data = {'Key': item_key,
            'Data': callback_data}
    # print(new_data)
    sync_map = 'ASRBotEvents'
    url = 'https://sync.twilio.com/v1/Services/' + twilio_sync_service_id + '/Maps/' + sync_map + '/Items'
    response = requests.request("POST", url, data=new_data, auth=HTTPBasicAuth(twilio_account_sid, twilio_auth_token))
    print(response.text)
    return 'OK'


######
##### Directory for static assets for Dashboard
@app.route('/<path:path>')
def send_js(path):
    print (path)
    return send_from_directory('static', path)


#### sync token
#############
@app.route('/token')
def token():
    # get the userid from the incoming request
    identity = request.values.get('identity', None)
    # Create access token with credentials
    token = AccessToken(twilio_account_sid, twilio_api_key, twilio_api_secret, identity=identity)
    # Create a Sync grant and add to token
    sync_grant = SyncGrant(service_sid=twilio_sync_service_id)
    token.add_grant(sync_grant)
    # Return token info as JSON
    return jsonify(identity=identity, token=token.to_jwt().decode('utf-8'))
								  
#####
##### AWS Polly for Text to Speech
##### This function calls Polly and then streams out the in-memory media in mp3 format
#####
@app.route('/polly_text2speech', methods=['GET', 'POST'])
def polly_text2speech():
    text = request.args.get('text', "Hello! Invalid request. Please provide the TEXT value")
    voiceid = request.args.get('polly_voiceid', "Joanna")
    region = request.args.get('region', "us-east-1")
    # Create a client using the credentials and region
    polly = boto3.client("polly", aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_key, region_name=region)
    # Request speech synthesis
    response = polly.synthesize_speech(Text=text, SampleRate="8000", OutputFormat="mp3", VoiceId=voiceid)

    # Access the audio stream from the response
    if "AudioStream" in response:
        # Note: Closing the stream is important as the service throttles on the
        # number of parallel connections. Here we are using contextlib.closing to
        # ensure the close method of the stream object will be called automatically
        # at the end of the with statement's scope.
        def generate():
            with closing(response["AudioStream"]) as dmp3:
                data = dmp3.read(1024)
                while data:
                    yield data
                    data = dmp3.read(1024)
        return Response(generate(), mimetype="audio/mpeg")
    else:
        # The response didn't contain audio data, exit gracefully
        print("Could not stream audio")
        return "Error"

@app.route('/retrieve_asr_details', methods=['GET', 'POST'])
def retrievetasrdetails():
    if (access_key == request.values.get('access_key', None)):
        sync_map_details = []
        client = Client(twilio_account_sid, twilio_auth_token)
        sync_map = 'ASRBotEvents'
        map_items = client.sync.services(twilio_sync_service_id).sync_maps(sync_map).sync_map_items.list(page_size=100)
        count = 0
        for item in map_items:
            sync_map_details.append(item.data)   
            # print (item.data)
            count +=1
            print (count)
        return json.dumps(sync_map_details)
    else:
        return 'Invalid Credential'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug = True)

